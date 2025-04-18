import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_mail import Mail, Message



email_bp = Blueprint('email', __name__)

mail = None  # We will initialize this in `app.py`

def init_mail(app):
    """Initialize Flask-Mail with the given app."""
    global mail
    mail = Mail(app)

def send_email(subject, recipient, body):
    """Send an email using Flask-Mail."""
    if mail is None:
        raise ValueError("Mail has not been initialized. Call init_mail(app) first.")

    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)


# Load subscriptions from a JSON file
subscriptions = []

def load_subscriptions():
    global subscriptions
    try:
        with open("subscriptions.json", "r") as file:
            subscriptions = json.load(file)
    except FileNotFoundError:
        subscriptions = []

def save_subscriptions():
    with open("subscriptions.json", "w") as file:
        json.dump(subscriptions, file)

@email_bp.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    email = data.get("email")
    selected_crags = data.get("selectedCrags", [])

    if not email or not selected_crags:
        return jsonify({"error": "Missing email or crag selections"}), 400

    subscriptions.append({"email": email, "selectedCrags": selected_crags})
    save_subscriptions()

    return jsonify({"message": "Subscribed successfully!"}), 200  # ✅ Ensure JSON response


# Function to fetch weather data
def fetch_weather(crag):
    api_key = "your_weather_api_key"
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={crag['lat']},{crag['lon']}"
    
    try:
        response = requests.get(url)
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch weather for {crag['name']}: {e}")
        return None

# Function to check weather and send alerts
def check_and_send_alerts():
    load_subscriptions()
    for subscription in subscriptions:
        for crag in subscription["selectedCrags"]:
            weather_data = fetch_weather(crag)
            if weather_data and "temperature" in weather_data and weather_data["temperature"] > 15:
                send_email(subscription["email"], f"Climbing Alert for {crag['name']}", f"The weather is perfect for climbing at {crag['name']}!")

# Set up a background scheduler to run every day at 8 AM
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_alerts, "interval", hours=24, start_date=datetime.now() + timedelta(seconds=60))
scheduler.start()
