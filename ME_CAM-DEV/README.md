### by MangiafestoElectronics LLC

# 📸 ME Camera (ME_CAM)
A secure, plug-and-play smart camera system for Raspberry Pi Zero 2 W, Pi 4, and Pi 5 with:

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
- Named face recognition on Raspberry Pi 4 and Pi 5
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
- Raspberry Pi Zero 2 W, Raspberry Pi 4, or Raspberry Pi 5
- Pi Camera Module or USB camera
- 16GB+ microSD card
- Optional: battery pack, case, PoE splitter

---

## 🧑‍💻 Software Requirements
- Raspberry Pi OS Lite (Bullseye, Bookworm, or newer)
- Python 3.9 or newer
- Camera stack supplied by Raspberry Pi OS (`libcamera-apps` or `rpicam-apps`)

Face recognition is available on Pi 4 and Pi 5. The setup script installs its optional runtime on those boards. In Settings, enable face recognition and upload one clear JPG or PNG per person; each filename (without its extension) is used as that person's name.

---

## 🔧 Installation (Fresh SD Card)

### 1. Flash Raspberry Pi OS Lite
Use Raspberry Pi Imager:
