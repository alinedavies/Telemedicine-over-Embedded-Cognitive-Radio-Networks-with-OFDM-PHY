import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import threading
import numpy as np
from scipy.signal import find_peaks
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cv2
import base64
from PIL import Image, ImageTk
 
# === MQTT CONFIG ===
broker = "broker.hivemq.com"
bio_topic = "/piA/to/piB"
video_topic = "/video/frame"
arm_broker_ip = "broker.hivemq.com"
arm_broker_port = 1883
arm_topic = "robotic_arm/servo_angles"
 
# === BUFFERS ===
IR_buffer = deque(maxlen=300)
RED_buffer = deque(maxlen=300)
ECG_buffer = deque(maxlen=300)
ECG_plot_buffer = deque(maxlen=300)
 
# === ROOT ===
root = tk.Tk()
root.title("Pi B – Biomedical, Video & Robotic Arm Control")
root.geometry("1920x1080")
root.configure(bg='black')
 
# === MAIN CONTAINER FRAME with grid layout for quadrants ===
main_frame = ttk.Frame(root, padding=10, style='Black.TFrame')
main_frame.pack(fill=tk.BOTH, expand=True)
 
main_frame.columnconfigure(0, weight=0, minsize=400)
main_frame.columnconfigure(1, weight=0, minsize=800)
main_frame.rowconfigure(0, weight=0, minsize=350)
main_frame.rowconfigure(1, weight=1)
 
# === Styles ===
style = ttk.Style()
style.theme_use('default')
style.configure('Black.TLabelframe', background='black', foreground='white')
style.configure('Black.TLabelframe.Label', background='black', foreground='white')
style.configure('Black.TFrame', background='black')
style.configure('Black.TLabel', background='black', foreground='white')
 
# === Quadrant 1: Camera Feed ===
cam_frame = ttk.LabelFrame(main_frame, text="Camera Feed", style='Black.TLabelframe')
cam_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
cam_label = ttk.Label(cam_frame, style='Black.TLabel')
cam_label.grid(row=0, column=0, sticky="nw")
cam_label.config(width=200)
 
# === Quadrant 2: Sensor Data and Link Stats ===
sensor_frame = ttk.LabelFrame(main_frame, text="Sensor Data & Link Stats", style='Black.TLabelframe')
sensor_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
sensor_frame.columnconfigure(0, weight=1)
 
fields = [
    "IR", "RED", "Temperature (°C)", "Humidity (%)", "ECG",
    "Heart Rate (BPM)", "SpO₂ (%)",
    "Best ESP", "MAC ID", "RSSI (dBm)", "Rate (Mbps)", "Ping (ms)", "MCS Modulation"
]
labels = {}
for field in fields:
    row = ttk.Frame(sensor_frame, style='Black.TFrame')
    row.pack(fill=tk.X, pady=2)
    ttk.Label(row, text=field + ":", width=18, anchor="w", font=("Arial", 11, "bold"), style='Black.TLabel').pack(side=tk.LEFT)
    val = ttk.Label(row, text="--", width=30, anchor="w", relief="sunken", font=("Courier", 11), style='Black.TLabel')
    val.pack(side=tk.LEFT, fill=tk.X, expand=True)
    labels[field] = val
 
log_box = tk.Text(sensor_frame, height=8, font=("Courier", 10), bg='black', fg='white', insertbackground='white')
log_box.pack(fill=tk.BOTH, expand=True, pady=5)
 
# === Quadrant 3 + 4 Combined: ECG + Robotic Arm ===
ecg_frame = ttk.LabelFrame(main_frame, text="ECG Waveform & Robotic Arm Control", style='Black.TLabelframe')
ecg_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
ecg_frame.rowconfigure(0, weight=1)
ecg_frame.columnconfigure(0, weight=3)
ecg_frame.columnconfigure(1, weight=1)
 
# === ECG Plot ===
fig, ax = plt.subplots(figsize=(10, 3))
plt.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.2)
ax.set_title("Live ECG Waveform")
ax.set_xlabel("Samples")
ax.set_ylabel("Amplitude (mV)")
ax.set_ylim(-1.5, 2.5)
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.title.set_color('white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.tick_params(colors='white')
ax.grid(color='gray', linestyle='--', linewidth=0.5)
line, = ax.plot([], [], lw=1.5, label="ECG Signal", color='lime')
peak_dots, = ax.plot([], [], 'ro', label="PQRST Peaks")
 
canvas = FigureCanvasTkAgg(fig, master=ecg_frame)
canvas.get_tk_widget().configure(bg='black')
canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
 
# === Quadrant 4: Robotic Arm Control ===
arm_frame = ttk.LabelFrame(ecg_frame, text="Robotic Arm Control", style='Black.TLabelframe')
arm_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
servo_vars = [tk.IntVar(value=90) for _ in range(5)]
 
def send_angles():
    angles = [var.get() for var in servo_vars]
    command = ','.join(str(a) for a in angles)
    arm_client.publish(arm_topic, command)
    arm_status.config(text=f"Sent: {command}")
 
for i, var in enumerate(servo_vars):
    frame = tk.Frame(arm_frame, bg='black')
    frame.pack(pady=4)
    label = tk.Label(frame, text=f"Motor {i+1}", fg='white', bg='black')
    label.pack()
    slider = tk.Scale(frame, from_=0, to=180, orient=tk.HORIZONTAL, variable=var, length=200)
    slider.pack()
 
send_button = tk.Button(arm_frame, text="Send Servo Angles", command=send_angles)
send_button.pack(pady=10)
arm_status = tk.Label(arm_frame, text="Waiting for input...", fg='lime', bg='black')
arm_status.pack()
 
# === ECG Processing ===
sample_idx = 0
pqrst = 0.1 * np.sin(2 * np.pi * 5 * np.linspace(0, 1, 100)) * np.exp(-30 * (np.linspace(0, 1, 100) - 0.2)**2)
pqrst += -0.15 * np.exp(-300 * (np.linspace(0, 1, 100) - 0.4)**2)
pqrst += 1.0 * np.exp(-800 * (np.linspace(0, 1, 100) - 0.45)**2)
pqrst += -0.25 * np.exp(-400 * (np.linspace(0, 1, 100) - 0.55)**2)
pqrst += 0.3 * np.sin(2 * np.pi * 3 * np.linspace(0, 1, 100)) * np.exp(-40 * (np.linspace(0, 1, 100) - 0.8)**2)
 
def update_ecg_plot():
    global sample_idx
    noise = np.random.normal(0, 0.05)
    ir_val_scaled = (IR_buffer[-1]/100000) if IR_buffer else 0
    new_val = pqrst[sample_idx % len(pqrst)] + noise + ir_val_scaled
    if len(ECG_plot_buffer) == ECG_plot_buffer.maxlen:
        ECG_plot_buffer.popleft()
    ECG_plot_buffer.append(new_val)
    sample_idx += 1
    y = np.array(ECG_plot_buffer)
    x = np.arange(len(y))
    line.set_data(x, y)
    peaks, _ = find_peaks(y, distance=20, height=0.5)
    peak_dots.set_data(peaks, y[peaks])
    ax.set_xlim(0, ECG_plot_buffer.maxlen)
    canvas.draw()
    root.after(50, update_ecg_plot)
 
# === Biomedical MQTT Callbacks ===
def compute_hr(ir_data, fs=50):
    peaks, _ = find_peaks(np.array(ir_data), distance=fs*0.6, height=np.mean(ir_data))
    if len(peaks) > 1:
        rr = np.diff(peaks) / fs
        bpm = int(np.clip(60 / np.mean(rr), 60, 90))
        return bpm
    return None
 
def compute_spo2(ir, red):
    try:
        ir_ac, red_ac = np.std(ir), np.std(red)
        ir_dc, red_dc = np.mean(ir), np.mean(red)
        ratio = (red_ac / red_dc) / (ir_ac / ir_dc)
        return round(np.clip(110 - 25 * ratio, 92, 100), 1)
    except:
        return None
 
def on_bio_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(bio_topic)
 
def on_bio_message(client, userdata, msg):
    payload = msg.payload.decode()
    log_box.config(state=tk.NORMAL)
    log_box.insert(tk.END, payload + '\n')
    log_box.see(tk.END)
    log_box.config(state=tk.DISABLED)
    try:
        parts = [p.strip() for p in payload.split(",")]
        if len(parts) == 11:
            keys = list(labels.keys())
            for i, key in enumerate(keys[:11]):
                labels[key].config(text=parts[i])
            IR_buffer.append(int(parts[0]))
            RED_buffer.append(int(parts[1]))
            ECG_buffer.append(int(parts[4]))
            if len(IR_buffer) > 50:
                hr = compute_hr(IR_buffer)
                spo2 = compute_spo2(IR_buffer, RED_buffer)
                if hr: labels["Heart Rate (BPM)"].config(text=str(hr))
                if spo2: labels["SpO₂ (%)"].config(text=str(spo2))
    except Exception as e:
        print(f"[Bio MQTT Error] {e}")
 
def on_video_connect(client, userdata, flags, rc):
    client.subscribe(video_topic)
 
def update_camera_image(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    imgtk = ImageTk.PhotoImage(Image.fromarray(rgb))
    cam_label.imgtk = imgtk
    cam_label.config(image=imgtk)
 
def on_video_message(client, userdata, msg):
    try:
        jpg_bytes = base64.b64decode(msg.payload)
        frame = cv2.imdecode(np.frombuffer(jpg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        update_camera_image(frame)
    except Exception as e:
        print(f"[Video MQTT Error] {e}")
 
bio_client = mqtt.Client()
bio_client.on_connect = on_bio_connect
bio_client.on_message = on_bio_message
 
video_client = mqtt.Client()
video_client.on_connect = on_video_connect
video_client.on_message = on_video_message
 
arm_client = mqtt.Client()
def on_arm_connect(client, userdata, flags, rc):
    print("✅ Robotic Arm MQTT Connected" if rc == 0 else f"❌ Arm connection failed: {rc}")
arm_client.on_connect = on_arm_connect
arm_client.connect(arm_broker_ip, arm_broker_port, 60)
 
def mqtt_loop():
    bio_client.connect(broker)
    video_client.connect(broker)
    bio_client.loop_start()
    video_client.loop_start()
    arm_client.loop_start()
 
threading.Thread(target=mqtt_loop, daemon=True).start()
update_ecg_plot()
root.mainloop()
