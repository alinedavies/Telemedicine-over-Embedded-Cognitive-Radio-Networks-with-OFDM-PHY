# app.py
from flask import Flask, render_template, request, jsonify
import threading
import time
import base64
import cv2
import numpy as np
import paho.mqtt.client as mqtt
from collections import deque
import csv, os

app = Flask(__name__)

# === MQTT CONFIG ===
broker = "broker.hivemq.com"
bio_topic = "/piA/to/piB"
video_topic = "/video/frame"
arm_topic = "robotic_arm/servo_angles"

# === Buffers ===
IR_buffer = deque(maxlen=300)
RED_buffer = deque(maxlen=300)
ECG_plot_buffer = deque(maxlen=300)
current_frame = None
bio_data = {}

# === Synthetic ECG ===
def generate_ecg_waveform(fs=250, duration=10):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    ecg = np.zeros_like(t)
    for beat_start in np.arange(0, duration, 0.8):
        idx = (t >= beat_start) & (t < beat_start + 0.8)
        beat_t = t[idx] - beat_start
        qrs = 0.1 * np.sin(2 * np.pi * 5 * beat_t) * np.exp(-30 * (beat_t - 0.2)**2)
        qrs += -0.15 * np.exp(-300 * (beat_t - 0.35)**2)
        qrs += 1.0 * np.exp(-800 * (beat_t - 0.4)**2)
        qrs += -0.25 * np.exp(-400 * (beat_t - 0.5)**2)
        qrs += 0.3 * np.sin(2 * np.pi * 3 * beat_t) * np.exp(-40 * (beat_t - 0.7)**2)
        ecg[idx] += qrs
    ecg += np.random.normal(0, 0.02, size=ecg.shape)
    return ecg.tolist()

synthetic_ecg = generate_ecg_waveform()

# === Disease Dataset ===
disease_symptoms = {}
def load_dataset(path="dataset.csv"):
    global disease_symptoms
    disease_symptoms = {}
    if not os.path.exists(path):
        return
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            disease = row['Disease'].strip().lower()
            symptoms = set()
            for i in range(1, 18):
                sym = row.get(f'Symptom_{i}')
                if sym and sym.strip():
                    symptoms.add(sym.strip().lower())
            disease_symptoms[disease] = symptoms
load_dataset()

def predict_disease(symptoms_input):
    user_symptoms = set(s.strip().lower() for s in symptoms_input.split(',') if s.strip())
    best, predicted = 0, None
    for disease, symptoms in disease_symptoms.items():
        overlap = len(user_symptoms & symptoms)
        if overlap > best:
            best, predicted = overlap, disease
    if predicted:
        return f"Predicted: {predicted.title()} (matched {best} symptoms)"
    return "No match found"

# === MQTT HANDLERS ===
def on_bio_message(client, userdata, msg):
    global bio_data
    payload = msg.payload.decode()
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) >= 11:
        keys = ["IR", "RED", "Temp", "Humidity", "ECG", "HR", "SpO2", "ESP", "MAC", "RSSI", "Rate"]
        bio_data = dict(zip(keys, parts[:11]))
        try:
            IR_buffer.append(int(parts[0]))
            RED_buffer.append(int(parts[1]))
            ECG_plot_buffer.append(float(parts[4]))
        except:
            pass

def on_video_message(client, userdata, msg):
    global current_frame
    try:
        jpg_bytes = base64.b64decode(msg.payload)
        frame = cv2.imdecode(np.frombuffer(jpg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        _, jpeg = cv2.imencode('.jpg', frame)
        current_frame = base64.b64encode(jpeg.tobytes()).decode('utf-8')
    except:
        pass

mqtt_client = mqtt.Client()
mqtt_client.message_callback_add(bio_topic, on_bio_message)
mqtt_client.message_callback_add(video_topic, on_video_message)
mqtt_client.connect(broker, 1883, 60)
mqtt_client.subscribe(bio_topic)
mqtt_client.subscribe(video_topic)
mqtt_client.loop_start()

# === ROUTES ===
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/telemedicine')
def telemedicine():
    return render_template("telemedicine.html")

@app.route('/assistant')
def assistant():
    return render_template("assistant.html")

@app.route('/api/bio')
def api_bio():
    return jsonify(bio_data)

@app.route('/api/ecg')
def api_ecg():
    synthetic_ecg.append(synthetic_ecg.pop(0))
    return jsonify(synthetic_ecg[:300])

@app.route('/api/frame')
def api_frame():
    return jsonify({"img": current_frame})

@app.route('/api/send_angles', methods=['POST'])
def send_angles():
    angles = request.json.get("angles", [])
    if angles and isinstance(angles, list):
        mqtt_client.publish(arm_topic, ",".join(map(str, angles)))
        return "OK"
    return "Fail", 400

@app.route('/predict', methods=['POST'])
def predict():
    symptoms = request.form.get("symptoms", "")
    result = predict_disease(symptoms)
    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
