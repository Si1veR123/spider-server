from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import timedelta

DB_PATH = "db.sqlite3"
PICTURES_PATH = "static/pictures/"
PASSWORD = os.environ.get("SPIDER_SERVER_PASSWORD")
if not PASSWORD:
    raise ValueError("SPIDER_SERVER_PASSWORD environment variable not set")

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

    return row

def get_latest_picture_url():
    pictures = sorted(filter(lambda f: not f.endswith("_small.jpg"), os.listdir(PICTURES_PATH)), reverse=True)
    if pictures:
        recent_picture = pictures[0]
        return f"/static/pictures/{recent_picture}"
    return None

app = Flask(__name__)
app.secret_key = os.environ.get("SPIDER_SERVER_SECRET_KEY")
if not app.secret_key:
    raise ValueError("SPIDER_SERVER_SECRET_KEY environment variable not set")
app.permanent_session_lifetime = timedelta(days=7)

# AUTHENTICATION

@app.before_request
def require_login():
    # Allow /auth without login
    if request.endpoint == "auth":
        return
    # If not logged in, redirect to /auth
    if not session.get("logged_in"):
        return redirect(url_for("auth"))

@app.route("/_auth_check")
def auth_check():
    if session.get("logged_in"):
        return "", 204
    return "", 401

@app.route("/auth", methods=["GET", "POST"])
def auth():
    error = None
    if request.method == "POST":
        print(request.form.get("password"), PASSWORD)
        if request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("index"))
        else:
            error = "Incorrect password"
    return render_template("auth.html", error=error)

# API

@app.route("/data/latest")
def latest_data():
    reading = get_latest_reading()
    recent_picture_url = get_latest_picture_url()

    if reading is None and recent_picture_url is None:
        return {"error": "No readings/pictures found"}, 404

    return {
        "timestamp": reading["timestamp"] if reading else None,
        "temperature": reading["temperature"] if reading else None,
        "humidity": reading["humidity"] if reading else None,
        "recent_picture": recent_picture_url
    }

@app.route("/data/history")
def history_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp, temperature, humidity
        FROM readings
        ORDER BY timestamp DESC
    """)

    rows = cur.fetchall()
    conn.close()

    data_point_count = request.args.get("n", default=100, type=int) - 1

    total_rows = len(rows)
    if total_rows == 0:
        return {"history": []}
    
    if total_rows <= data_point_count:
        sampled_rows = rows
    else:
        step = total_rows / data_point_count
        sampled_rows = [rows[min(int(i * step), total_rows - 1)] for i in range(data_point_count)]

    history_data = []
    for row in sampled_rows:
        history_data.append({
            "timestamp": row["timestamp"],
            "temperature": row["temperature"],
            "humidity": row["humidity"]
        })

    # Ensure most recent reading is included
    history_data.append({
        "timestamp": rows[0]["timestamp"],
        "temperature": rows[0]["temperature"],
        "humidity": rows[0]["humidity"]
    })

    return {"history": history_data}

# PAGES

@app.route("/")
def index():
    reading = get_latest_reading()
    recent_picture_url = get_latest_picture_url()

    if reading:
        recent_temperature = f"{reading["temperature"]:.2f} °C"
        recent_rh = f"{reading["humidity"]:.2f} %"
    else:
        recent_temperature = "None"
        recent_rh = "None"

    return render_template(
        "main.html",
        recent_temperature=recent_temperature,
        recent_rh=recent_rh,
        recent_picture=recent_picture_url
    )

@app.route("/history")
def history():
    return render_template("history.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=False)