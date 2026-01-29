"""
Take sensor Temperature/Relative Humidity readings from a ENV-IV sensor (SHT40)
"""

import sqlite3
import time
import os
from datetime import datetime, timedelta
from smbus2 import SMBus, i2c_msg

DB_FILE = "../db.sqlite3"
FREQUENCY = 10
MAX_HISTORY = 12 * 60 * 60

I2C_BUS = 1
SHT40_ADDR = 0x44
# high precision
CMD_MEASURE = 0xFD

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

    while True:
        try:
            temp, humidity = read_sensor()
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] Temp: {temp:.2f}°C, Humidity: {humidity:.2f}%")

            insert_reading(timestamp, temp, humidity)
            cleanup_old_readings()
        except Exception as e:
            print(f"Error reading sensor or saving data: {e}")

        time.sleep(FREQUENCY)

if __name__ == "__main__":
    main()