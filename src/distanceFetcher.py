import openrouteservice
import json
import time
from dotenv import load_dotenv
from pathlib import Path
import os

API_KEY = os.getenv("API_KEY")
client = openrouteservice.Client(key=API_KEY)

# Open and load crag data
input_file = "newyorkAreaNameGPS.json"
output_file = "nycToNY.json"

try:
    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)
        mtl_to_VT = [{"name": crag["name"], "lat": crag["lat"], "lon": crag["lon"], "climbs": crag.get("climbs", 0), "country": "US"} for crag in data]
except FileNotFoundError:
    print("Cannot find JSON file to load from.")
    exit()

ORIGIN = (40.7128, -74.0060)  
distances = []
api_call_count = 0  # Track API call count

for crag in mtl_to_VT:
    coords = [[ORIGIN[1], ORIGIN[0]], [crag["lon"], crag["lat"]]]
    
    # Retry logic with delay
    retries = 3
    for attempt in range(retries):
        try:
            route = client.directions(
                coordinates=coords,
                profile="driving-car",
                format="geojson"
            )
            distance_km = route["features"][0]["properties"]["segments"][0]["distance"] / 1000
            crag["distance"] = round(distance_km, 2)
            distances.append(crag)
            api_call_count += 1  # Increment API call count
            
            # Pause after every 40 API calls
            if api_call_count % 30 == 0:
                print("Rate limit reached, pausing for 70 seconds...")
                time.sleep(70)
            
            break  # Break on success
        except openrouteservice.exceptions._OverQueryLimit:
            if attempt < retries - 1:
                print(f"Rate limit exceeded. Retrying... ({attempt+1}/{retries})")
                time.sleep(5 * (attempt + 1))  # Exponential backoff
            else:
                print(f"Rate limit exceeded. Skipping {crag['name']}.")
        except Exception as e:
            print(f"Error fetching API for {crag['name']}: {e}")
            break  # Skip this crag if error occurs

# Save results including climb counts
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(distances, file, indent=4, ensure_ascii=False)

print(f"Data successfully saved to {output_file}")
