from flask import Flask, render_template
import sqlite3
import os

DB_PATH = "db.sqlite3"
PICTURES_PATH = "pictures/"

def get_latest_reading():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp, temperature, humidity
        FROM readings
        ORDER BY timestamp DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "timestamp": row["timestamp"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
    }

app = Flask(__name__)

@app.route("/")
def index():
    reading = get_latest_reading()

    # sort filenames by time
    pictures = sorted(os.listdir(PICTURES_PATH), reverse=True)

    if pictures:
        recent_picture = pictures[0]
        recent_picture_url = f"/static/pictures/{recent_picture}"
    else:
        recent_picture_url = None

    return render_template(
        "main.html",
        recent_rh = f"{reading['humidity']}%" if reading else "None",
        recent_temperature = f"{reading['temperature']}°C" if reading else "None",
        recent_picture=recent_picture_url
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=False)