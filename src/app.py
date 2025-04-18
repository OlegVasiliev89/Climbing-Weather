import os
import json
import requests
import math
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)

# Supabase setup
DB_URI = os.getenv("DB_URI")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Email notofication setup
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS")
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")


mail = Mail(app)

# Main function of the app allowing users to choose their city of departure, time / distance they are looking to drive, dates in the next 7 days that interest them and potentially temperature conditions if they are searching for a single day.

@app.route("/find-crags", methods=["POST"])
def find_crags():
    try:
        data = request.json
        print("Received data:", data)

        hours = data.get("hours")
        origin = data.get("origin")
        date_from = data.get("dateFrom")
        date_to = data.get("dateTo")
        min_temp = data.get("minTemp")
        max_temp = data.get("maxTemp")
        min_temp = int(min_temp) if min_temp is not None else None
        max_temp = int(max_temp) if max_temp is not None else None

        if not all([hours, origin, date_from, date_to]):
            return jsonify({"error": "Missing required fields"}), 400

        max_distance_km = int(hours) * 100

        # Load crags based on origin
        crags = load_crags_for_origin(origin)

        final_crags = []
        for crag in crags:
            if crag["distance"] <= max_distance_km:
                weather = get_weather(crag["lat"], crag["lon"], date_from, date_to)

                if "error" not in weather:
                    if date_from == date_to and min_temp is not None and max_temp is not None:
                        day_weather = weather.get(date_from)
                        if day_weather:
                            temp = day_weather["temperature"]
                            if not (min_temp <= temp <= max_temp):
                                continue

                final_crags.append({
                    "name": crag["name"],
                    "distance": crag["distance"],
                    "climbs": crag.get("climbs", 0),
                    "lat": crag["lat"],
                    "lon": crag["lon"],
                    "weather": weather
                })

        return jsonify(final_crags)

    except Exception as e:
        print("Error in /find-crags:", e)
        return jsonify({"error": str(e)}), 500
    
# Notofication system via email where users can sign up and be daily updated via their email of changes in temperature or conditions for selected climbing areas on desired dates

@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    print("Received Data:", data)

    email = data.get("email")
    date_from = data.get("dateFrom")
    date_to = data.get("dateTo")
    selected_crags = data.get("selectedCrags", [])

    success = save_selected_crags_to_db(email, selected_crags, date_from, date_to)

    if success:
        send_email(
        subject="Climbing Crag Subscription Confirmed",
        recipient=email,
        body=f"Hi! You've successfully subscribed to receive updates for crags from {date_from} to {date_to}.\n\nSelected Crags:\n" + 
             "\n".join([crag["name"] for crag in selected_crags])
    )
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to save crags"}), 500


def load_crags_for_origin(city):
    try:
        with open(Path(__file__).parent / "originCities.json", "r") as f:
            origin_map = json.load(f)

        filenames = origin_map.get(city, [])
        crags = []
        for filename in filenames:
            try:
                filepath = Path(__file__).parent / "distances" / filename
                with open(filepath, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    crags.extend([
                        {"name": crag["name"], "lat": crag["lat"], "lon": crag["lon"], "distance": crag["distance"], "climbs": crag["climbs"]}
                        for crag in data
                    ])
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        return crags
    except Exception as e:
        print(f"Failed to load crags for {city}: {e}")
        return []


def get_weather(lat, lon, date_from, date_to):
    url = f"https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {"error": "Failed to retrieve weather"}

    weather_data = response.json()
    forecast_dict = {}

    for forecast in weather_data["list"]:
        forecast_date = forecast["dt_txt"].split(" ")[0]
        if date_from <= forecast_date <= date_to:
            forecast_dict[forecast_date] = {
                "temperature": math.ceil(forecast["main"]["temp"]),
                "description": forecast["weather"][0]["description"],
                "icon": f"http://openweathermap.org/img/wn/{forecast['weather'][0]['icon']}@2x.png"
            }

    return forecast_dict if forecast_dict else {"error": "No forecast available for selected dates"}

def send_email(subject, recipient, body):
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")


def save_selected_crags_to_db(user_email, selected_crags, date_from, date_to):
    try:
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()

        for crag in selected_crags:
            weather = crag.get("weather", {})
            conditions = None
            temperature = None
            lat = crag.get("lat")
            lon = crag.get("lon")

            if weather:
                first_day_key = next(iter(weather))
                first_day = weather[first_day_key]
                conditions = first_day.get("description")
                temperature = first_day.get("temperature")

            query = """
            INSERT INTO user_subscriptions (crag_name, date_from, date_to, conditions, temperature, created_at, email, lat, lon)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s);
            """
            cursor.execute(query, (crag["name"], date_from, date_to, conditions, temperature, user_email, lat, lon))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        import traceback
        print("Error saving selected crags:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    app.run(debug=True)
