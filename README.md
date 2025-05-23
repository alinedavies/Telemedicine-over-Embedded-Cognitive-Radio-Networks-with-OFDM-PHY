# Telemedicine-over-Embedded-Cognitive-Radio-Networks-with-OFDM-PHY
# 📡 Embedded Telemedicine using Cognitive Radio Networks with OFDM PHY

A secure, real-time embedded telemedicine framework leveraging Cognitive Radio Networks (CRNs) and Orthogonal Frequency Division Multiplexing (OFDM) PHY to provide remote healthcare access in bandwidth-constrained environments.


## Project Overview

In underserved and remote regions, access to real-time healthcare is limited by unreliable communication infrastructure and fixed-spectrum wireless systems. This project addresses these issues by:

- Integrating biomedical sensors with ESP32-C6 modules (Wi-Fi 6 enabled)
- Enabling intelligent, dynamic spectrum access through CRNs
- Using OFDM PHY for low-latency and robust data transmission
- Supporting real-time patient monitoring and robotic assistance via Raspberry Pi GUI

## Key Features

- Real-time acquisition of ECG, SpO₂, and Temperature data
- Adaptive wireless link selection using RSSI and SNR
- Live video streaming via ESP32-CAM
- Doctor-side GUI with real-time waveform plots and robotic arm control
- MQTT-based communication over Wi-Fi 6 with OFDM PHY
- 22% power efficiency gain and 31% latency reduction vs. fixed-spectrum systems

## Hardware Used

- **ESP32-C6** – Cognitive radio node with Wi-Fi 6 support
- **Raspberry Pi 4B** – Data aggregation, processing, GUI, and robotic control
- **AD8232** – ECG sensor module
- **MAX30102** – Pulse Oximeter (SpO₂ & Heart Rate)
- **DHT22** – Temperature & Humidity Sensor
- **ESP32-CAM** – For live video feed
- **Servo Motors** – Robotic Arm actuation

## Software Stack

| Component             | Description                              |
|----------------------|------------------------------------------|
| **Python 3**         | Main programming language (Raspberry Pi) |
| **C/C++ (ESP32)**    | Firmware for sensor interfacing & CRN    |
| **Tkinter**          | GUI for data visualization & control     |
| **OpenCV**           | Video feed decoding                      |
| **MQTT**             | Lightweight publish/subscribe messaging  |
| **MATLAB**           | Signal processing and validation         |

## Implementation Summary

- ECG, SpO₂, and temperature values are captured, preprocessed, and sent over Wi-Fi 6.
- Raspberry Pi selects the best ESP32-C6 link based on real-time MAC/PHY metrics.
- OFDM PHY layer ensures reliable and high-throughput communication.
- Tkinter-based GUI displays ECG waveform, sensor data, and robot controls.
- Robotic arm actions (UP/DOWN/CW/CCW) are controlled remotely via MQTT.

## Performance Highlights

| Metric                   | Improvement |
|--------------------------|-------------|
| Power Efficiency         | +22%        |
| Latency Reduction        | -31%        |
| ECG Accuracy             | >96%        |
| Video Feed Delay         | <150ms      |
| ESP Switching Time       | <2.5s       |


