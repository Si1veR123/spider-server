"""
Take sensor Temperature/Relative Humidity readings from a ENV-IV sensor (SHT40)
"""

import sqlite3
import time
import os
from datetime import datetime, timedelta
from smbus2 import SMBus, i2c_msg
import smtplib
from email.message import EmailMessage

# EMAIL WARNINGS
USING_GMAIL = True
GMAIL_USER = os.environ.get("GMAIL_USER")
if not GMAIL_USER:
    print("GMAIL_USER environment variable not set, email warnings disabled")
    USING_GMAIL = False

GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
if not GMAIL_APP_PASSWORD and USING_GMAIL:
    print("GMAIL_APP_PASSWORD environment variable not set, email warnings disabled")
    USING_GMAIL = False

GMAIL_RECIPIENT = os.environ.get("GMAIL_RECIPIENT")
if not GMAIL_RECIPIENT and USING_GMAIL:
    print("GMAIL_RECIPIENT environment variable not set, email warnings disabled")
    USING_GMAIL = False

SPIDER_WARNING_EMAIL_TEMPLATE = """
<html>
<body>
    <p>{message}</p>
    <ul>
    <li>Timestamp: {timestamp}</li>
    <li>Temperature: {temperature:.2f} °C</li>
    <li>Humidity: {humidity:.2f} %</li>
    </ul>
</body>
</html>
"""

MIN_TEMPERATURE = float(os.environ.get("MIN_TEMPERATURE", 19.0))
MAX_TEMPERATURE = float(os.environ.get("MAX_TEMPERATURE", 28.0))
MIN_HUMIDITY = float(os.environ.get("MIN_HUMIDITY", 50.0))
MAX_HUMIDITY = float(os.environ.get("MAX_HUMIDITY", 78.0))

# DATABASE CONFIG
DB_FILE = "../db.sqlite3"
FREQUENCY = 10
MAX_HISTORY = 12 * 60 * 60

# I2C CONFIG
I2C_BUS = 1
SHT40_ADDR = 0x44
# high precision
CMD_MEASURE = 0xFD

class EmailSender:
    def __init__(self, max_interval: int = 3 * 60 * 60):
        self.max_interval = max_interval
        self.active_warnings = {
            "humidity": None,
            "temperature": None
        }
        self.last_sent_times = {
            ("humidity", "low"): datetime.min,
            ("humidity", "high"): datetime.min,
            ("temperature", "low"): datetime.min,
            ("temperature", "high"): datetime.min,
        }
    
    def process_values(self, humidity: float, temperature: float):
        if humidity < MIN_HUMIDITY:
            self.active_warnings["humidity"] = "low"
        elif humidity > MAX_HUMIDITY:
            self.active_warnings["humidity"] = "high"
        else:
            # Remove humidity warnings if back to normal
            self.active_warnings["humidity"] = None

        if temperature < MIN_TEMPERATURE:
            self.active_warnings["temperature"] = "low"
        elif temperature > MAX_TEMPERATURE:
            self.active_warnings["temperature"] = "high"
        else:
            # Remove temperature warnings if back to normal
            self.active_warnings["temperature"] = None

        if not any(self.active_warnings.values()):
            return
        
        message = ""
        for key, value in self.active_warnings.items():
            if value is not None:
                message += f"{key.capitalize()} too {value}! "

        print("Warning message:", message)

        # Filter warnings by last sent time
        now = datetime.now()
        filtered_warnings = []
        for key, value in self.active_warnings.items():
            if value is not None and (now - self.last_sent_times[(key, value)]).total_seconds() > self.max_interval:
                filtered_warnings.append((key, value))

        if filtered_warnings:
            for warning in filtered_warnings:
                self.last_sent_times[warning] = now
            
            email = generate_warning_email_html(message, now.isoformat(), temperature, humidity)
            send_email(message, email, GMAIL_RECIPIENT)
            print("Sent warning email.")

def generate_warning_email_html(message, timestamp, temperature, humidity):
    return SPIDER_WARNING_EMAIL_TEMPLATE.format(
        message=message,
        timestamp=timestamp,
        temperature=temperature,
        humidity=humidity
    )

def send_email(subject: str, html: str, recipient: str):
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = recipient
    msg["Subject"] = subject

    # High importance
    msg["X-Priority"] = "1"
    msg["Importance"] = "High"
    msg["X-MSMail-Priority"] = "High"

    msg.set_content(html, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        try:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        except Exception as e:
            print(f"Error sending email: {e}")

def convert_temp(raw_value):
    centigrade = -45 + 175 * (raw_value / (2**16 - 1))
    return centigrade

def convert_humidity(raw_value):
    rh = -6 + 125 * (raw_value / (2**16 - 1))
    return rh

def read_sensor():
    with SMBus(I2C_BUS) as bus:
        # Send measurement command
        bus.write_byte(SHT40_ADDR, CMD_MEASURE)
        time.sleep(0.02)
        # Read the 6 byte response
        # Format: Temp MSB, Temp LSB, Temp CRC, RH MSB, RH LSB, RH CRC
        read = i2c_msg.read(SHT40_ADDR, 6)
        bus.i2c_rdwr(read)

    # Combine the bytes
    data = list(read)
    raw_temp = (data[0] << 8) | data[1]
    raw_humidity = (data[3] << 8) | data[4]

    return convert_temp(raw_temp), convert_humidity(raw_humidity)

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            timestamp TEXT PRIMARY KEY,
            temperature REAL,
            humidity REAL
        )
    """)
    conn.commit()
    conn.close()


def insert_reading(timestamp, temperature, humidity):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO readings (timestamp, temperature, humidity) VALUES (?, ?, ?)",
        (timestamp, temperature, humidity)
    )
    conn.commit()
    conn.close()


def cleanup_old_readings():
    cutoff = datetime.now() - timedelta(seconds=MAX_HISTORY)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM readings WHERE timestamp < ?", (cutoff.isoformat(),))
    conn.commit()
    conn.close()

def main():
    init_db()

    email_sender = EmailSender()

    while True:
        try:
            temp, humidity = read_sensor()
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] Temp: {temp:.2f}°C, Humidity: {humidity:.2f}%")

            if USING_GMAIL:
                email_sender.process_values(humidity, temp)

            insert_reading(timestamp, temp, humidity)
            cleanup_old_readings()
        except Exception as e:
            print(f"Error reading sensor or saving data: {e}")

        time.sleep(FREQUENCY)

if __name__ == "__main__":
    main()