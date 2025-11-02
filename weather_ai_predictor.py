import requests
import pandas as pd
import numpy as np
import datetime
from sklearn.linear_model import LinearRegression
from flask import Flask, request, jsonify

# 🔧 Konfigurasi Firebase & API
FIREBASE_URL = "https://siaga-banjir-b73a8-default-rtdb.asia-southeast1.firebasedatabase.app/"
API_KEY = "bb2dd84ca2541574dac0faffefcb4e45"

app = Flask(__name__)

# ===============================
# 🔹 Ambil Data Cuaca dari OpenWeatherMap
# ===============================
def get_openweather_data(lat, lon):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=id"
    print(f"📡 Mengambil data OWM: {url}")
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        return [{
            "local_datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "t": data["main"]["temp"],
            "hu": data["main"]["humidity"],
            "weather_desc": data["weather"][0]["description"].capitalize(),
        }]
    except Exception as e:
        print(f"❌ Gagal ambil data OWM: {e}")
        return []

# ===============================
# 🔹 Prediksi Cuaca Beberapa Hari ke Depan
# ===============================
def predict_next_days(data_owm, hari_prediksi=6):
    if not data_owm:
        return data_owm

    df = pd.DataFrame(data_owm)
    df["local_datetime"] = pd.to_datetime(df["local_datetime"])
    df["day_index"] = np.arange(len(df))
    df["t"] = pd.to_numeric(df["t"], errors="coerce")
    df["hu"] = pd.to_numeric(df["hu"], errors="coerce")

    X = df[["day_index"]]
    model_temp = LinearRegression().fit(X, df["t"])
    model_humid = LinearRegression().fit(X, df["hu"])

    preds = []
    last_date = df["local_datetime"].max()
    for i in range(1, hari_prediksi + 1):
        next_index = len(df) + i - 1
        next_day = last_date + datetime.timedelta(days=i)

        pred_temp = model_temp.predict([[next_index]])[0]
        pred_humid = model_humid.predict([[next_index]])[0]

        if pred_humid > 85:
            kondisi = "Hujan"
        elif pred_humid > 70:
            kondisi = "Berawan"
        else:
            kondisi = "Cerah"

        preds.append({
            "local_datetime": next_day.strftime("%Y-%m-%d 00:00:00"),
            "t": round(pred_temp, 1),
            "hu": round(pred_humid, 0),
            "weather_desc": kondisi
        })
    return data_owm + preds

# ===============================
# 🔹 Simpan ke Firebase Berdasarkan Lokasi
# ===============================
def simpan_ke_firebase(data, lat, lon):
    # 🔹 Format sama persis dengan Flutter (tiga angka di belakang koma)
    node_name = f"{lat:.3f}_{lon:.3f}".replace(".", "_")
    url = f"{FIREBASE_URL}/prediksi_cuaca/{node_name}.json"
    try:
        res = requests.put(url, json=list(data))
        if res.status_code == 200:
            print(f"✅ Data cuaca tersimpan di Firebase node: /prediksi_cuaca/{node_name}")
        else:
            print(f"❌ Gagal kirim ke Firebase: {res.text}")
    except Exception as e:
        print(f"🔥 Error Firebase: {e}")

# ===============================
# 🌍 Endpoint API — Terima Lokasi dari Flutter
# ===============================
@app.route("/prediksi", methods=["POST"])
def prediksi_lokasi():
    try:
        body = request.get_json()
        lat = float(body.get("lat"))
        lon = float(body.get("lon"))

        print(f"📍 Menerima permintaan prediksi untuk lokasi ({lat}, {lon})")

        data = get_openweather_data(lat, lon)
        hasil = predict_next_days(data)
        simpan_ke_firebase(hasil, lat, lon)

        return jsonify({"status": "success", "data": hasil})
    except Exception as e:
        print(f"❌ Error di endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ===============================
# 🚀 Jalankan Server Flask
# ===============================
if __name__ == "__main__":
    print("🚀 Server Cuaca + AI Dinamis aktif! (berdasarkan lokasi pengguna)")
    app.run(host="0.0.0.0", port=5000)
