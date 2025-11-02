# scripts/update_weather.py
import os, requests, datetime, time, json

OWM_KEY = os.environ.get("OPENWEATHER_API_KEY")
FIREBASE_URL = os.environ.get("FIREBASE_DB_URL")  # contoh: https://siaga-banjir-...asia-southeast1.firebasedatabase.app
LOCATIONS = os.environ.get("LOCATIONS", "")  # format: lat1,lon1;lat2,lon2  contoh: -5.1767,119.4286

if not OWM_KEY or not FIREBASE_URL or not LOCATIONS:
    print("Missing env vars. Set OPENWEATHER_API_KEY, FIREBASE_DB_URL, LOCATIONS")
    raise SystemExit(1)

def get_current(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric&lang=id"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    d = r.json()
    return {
        "local_datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "t": d["main"]["temp"],
        "hu": d["main"]["humidity"],
        "weather_desc": d["weather"][0]["description"].capitalize(),
    }

def make_predictions(current, days=6):
    # Sederhana: gunakan nilai hari ini sebagai prediksi untuk beberapa hari mendatang.
    out = [current]
    base_temp = current["t"]
    base_hu = current["hu"]
    for i in range(1, days+1):
        dt = (datetime.datetime.now() + datetime.timedelta(days=i)).strftime("%Y-%m-%d 00:00:00")
        out.append({
            "local_datetime": dt,
            "t": round(base_temp, 1),
            "hu": int(round(base_hu)),
            "weather_desc": current["weather_desc"]  # simple
        })
    return out

def node_name(lat, lon):
    return f"{round(float(lat),3):.3f}_{round(float(lon),3):.3f}".replace(".", "_")

def push_to_firebase(node, data):
    url = f"{FIREBASE_URL.rstrip('/')}/prediksi_cuaca/{node}.json"
    r = requests.put(url, json=data, timeout=15)
    r.raise_for_status()
    return r.text

def main():
    pairs = [p.strip() for p in LOCATIONS.split(";") if p.strip()]
    for p in pairs:
        lat, lon = p.split(",")
        print(f"[{time.strftime('%H:%M:%S')}] Processing {lat},{lon}")
        try:
            cur = get_current(lat, lon)
            hasil = make_predictions(cur, days=6)
            node = node_name(lat, lon)
            push_to_firebase(node, hasil)
            print(f"OK -> pushed {len(hasil)} items to /prediksi_cuaca/{node}")
        except Exception as e:
            print("ERROR:", e)

if __name__ == "__main__":
    main()
