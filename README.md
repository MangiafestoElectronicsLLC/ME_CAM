### by MangiafestoElectronics LLC

# 📸 ME Camera (ME_CAM)
A secure, plug‑and‑play Raspberry Pi Zero 2 W smart camera system with:

- Person‑only motion detection (AI‑powered)
- Encrypted local storage with retention control
- Email + Google Drive notifications
- Emergency clip sending
- First‑run setup wizard
- Auto‑boot service
- Multi‑camera dashboard (ME_CAM Hub)
- Mobile‑friendly web UI
- Optional WireGuard secure remote access

---

## 🚀 Features

### 🎯 Smart Detection
- Person‑only motion detection using TensorFlow Lite
- Smart motion filtering (no false triggers from leaves, shadows, etc.)
- Records only when a person is detected

### 🔐 Security
- PIN‑protected dashboard
- Optional WireGuard secure remote access
- Local encrypted storage (optional)

### ☁️ Notifications
- Email alerts with attached motion clips
- Google Drive uploads
- Emergency “Send to First Responders” button

### 🧰 Reliability
- Watchdog auto‑restarts camera pipeline
- Automatic cleanup of old recordings
- Systemd auto‑boot service

### 🖥 Multi‑Camera Support
- ME_CAM Hub dashboard for viewing multiple cameras

---

## 🧩 Hardware Requirements
- Raspberry Pi Zero 2 W (recommended)
- Pi Camera Module or USB camera
- 16GB+ microSD card
- Optional: battery pack, case, PoE splitter

---

## 🧑‍💻 Software Requirements
- Raspberry Pi OS **Legacy (Bullseye) Lite**
- Python 3.9
- OpenCV 4.5.1.48
- TensorFlow Lite Runtime 2.7.0

---

## 🔧 Installation (Fresh SD Card)

### 1. Flash Bullseye Lite
Use Raspberry Pi Imager:
