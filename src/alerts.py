from flask import Flask
from flask_mail import Mail, Message
import psycopg2
import requests
from datetime import date
import math
from dotenv import load_dotenv
from pathlib import Path
import os


load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Flask app setup
app = Flask(__name__)

# Mail setup
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS")
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# Database and API setup
DB_URI = os.getenv("DB_URI")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

def get_users_to_check():
    conn = psycopg2.connect(DB_URI)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, crag_name, date_from, conditions, temperature, email, lat, lon
        FROM user_subscriptions
        WHERE date_from >= CURRENT_DATE
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def get_weather_for_lat_lon_and_date(lat, lon, target_date):
    url = f"https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Error getting weather for {lat},{lon} on {target_date}")
        return None

    weather_data = response.json()
    for forecast in weather_data["list"]:
        forecast_date = forecast["dt_txt"].split(" ")[0]
        if forecast_date == str(target_date):
            return {
                "temperature": math.ceil(forecast["main"]["temp"]),
                "conditions": forecast["weather"][0]["description"]
            }

    print(f"No forecast data available for {target_date}")
    return None

def send_weather_alert(email, crag_name, date_from, old_temp, old_cond, new_temp, new_cond):
    msg = Message(subject='Weather Forecast Changed', recipients=[email])
    msg.body = f"""
Hi,

The weather forecast for {crag_name} on {date_from} has changed.

Original Forecast:
- Temperature: {old_temp}°C
- Conditions: {old_cond}

Updated Forecast:
- Temperature: {new_temp}°C
- Conditions: {new_cond}

Please check the latest forecast before planning your activities.

Regards,
Your Weather Monitor
"""
    mail.send(msg)

@app.route('/check-weather', methods=['GET'])
def check_weather():
    users = get_users_to_check()
    changes_sent = 0

    for user in users:
        user_id, crag_name, date_from, saved_conditions, saved_temp, email, lat, lon = user

        weather = get_weather_for_lat_lon_and_date(lat, lon, date_from)
        if not weather:
            continue

        new_temp = weather['temperature']
        new_conditions = weather['conditions']

        # Check if temperature or conditions changed significantly
        if abs(new_temp - saved_temp) > 1 or new_conditions.lower() != saved_conditions.lower():
            send_weather_alert(email, crag_name, date_from, saved_temp, saved_conditions, new_temp, new_conditions)
            changes_sent += 1

    return f"Checked {len(users)} forecasts. Emails sent: {changes_sent}\n"

if __name__ == '__main__':
    app.run(debug=True)
