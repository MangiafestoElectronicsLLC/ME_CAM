# ME_CAM: Secure Smart Camera System

A professional-grade security camera system for Raspberry Pi Zero 2 W with ArduCAM, featuring local encrypted storage, battery monitoring, and a beautiful SafeHome-style web dashboard.

## 🎯 Features

### Core Features
- **Motion Detection**: Real-time motion and person detection using OpenCV
- **Video Recording**: Automatic clip recording on motion (configurable retention)
- **Encrypted Storage**: Fernet symmetric encryption for all recordings on local SD card
- **Web Dashboard**: Professional SafeHome-style interface with live status and stream
- **Battery Monitoring**: Detects USB power bank via vcgencmd undervoltage detection
- **Thumbnail Previews**: Automatic first-frame extraction for video thumbnails
- **Live Stream**: MJPEG video stream endpoint for real-time monitoring
- **Emergency Alerts**: One-click SOS button for emergency contact
- **PIN Authentication**: Secure access control for web dashboard

### Optional Integrations (Configurable)
- **Email Alerts**: SMTP-based motion detection alerts
- **Google Drive Backup**: Automatic recording upload to cloud
- **WiFi Configuration**: Network setup interface (planned)
- **Bluetooth Support**: Remote control via Bluetooth (planned)
- **Webhooks**: Custom notification webhooks (framework ready)

### Security
- Encrypted local storage using Fernet (cryptography library)
- Session-based PIN authentication
- Auth-gated API endpoints
- Key management with auto-generation
- Secure configuration storage

---

## 📋 Hardware Requirements

- **Raspberry Pi Zero 2 W** (1.0 GHz quad-core, 512MB RAM)
- **ArduCAM USB Camera Module** (640x480 minimum recommended)
- **USB Power Bank** (for portable power, auto-detected)
- **SD Card** (16GB+ recommended for recordings)
- **Network**: WiFi via USB adapter or Ethernet via USB

---

## 🚀 Quick Start

### Deployment
1. Flash Raspberry Pi OS Bullseye on SD card using [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Update system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3-pip python3-opencv
   pip3 install cryptography loguru flask
   ```
3. Enable camera:
   ```bash
   sudo raspi-config  # Interfacing Options > Camera > Enable > Reboot
   ```
4. Deploy code:
   ```bash
   scp -r ME_CAM_DEV/* pi@raspberrypi.local:~/ME_CAM/
   ```
5. Run setup:
   ```bash
   cd ~/ME_CAM && python3 main.py
   ```
6. Access dashboard at `http://<pi-ip>:8080` (Default PIN: `1234`)

For detailed deployment steps, see [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📁 Project Structure

```
ME_CAM/
├── main.py                      # Entry point (starts watchdog + Flask)
├── camera_pipeline.py           # OpenCV motion/person detection & recording
├── watchdog.py                  # Pipeline lifecycle management
├── battery_monitor.py           # vcgencmd battery & external power detection
├── config_manager.py            # JSON config with thread-safe access
├── encryptor.py                 # Fernet encryption utility
├── thumbnail_gen.py             # First-frame video thumbnail extraction
├── motion_detector.py           # Motion detection algorithm
├── ai_person_detector.py        # Person detection (HOG/SSD)
├── face_detector.py             # Face detection (Haar cascades)
├── web/
│   ├── app.py                   # Flask server (auth, routes, API endpoints)
│   ├── static/
│   │   ├── style.css            # SafeHome-style dashboard CSS
│   │   └── thumbs/              # Generated video thumbnails (created at runtime)
│   └── templates/
│       ├── login.html           # PIN authentication page
│       ├── dashboard.html       # Main dashboard (status grid, live feed, recordings)
│       ├── config.html          # Settings page (email, Google Drive, WiFi, Bluetooth)
│       ├── first_run.html       # Setup wizard
│       └── fallback.html        # Error fallback
├── config/
│   ├── config_default.json      # Default configuration template
│   ├── config.json              # Active configuration (created at runtime)
│   ├── storage_key.key          # Fernet encryption key (auto-generated, keep safe!)
│   └── gdrive_credentials.json  # Google Drive API credentials (optional)
├── recordings/                  # Plaintext video clips (created at runtime)
├── recordings_encrypted/        # Encrypted video clips (created at runtime)
├── logs/                        # Loguru structured logs (created at runtime)
├── DEPLOYMENT.md                # Complete deployment & troubleshooting guide
├── FEATURE_CHECKLIST.md         # Implementation status & QA checklist
├── README.md                    # This file
└── requirements.txt             # Python dependencies
```

---

## 🎨 Dashboard Features

### Status Grid (5 Cards)
1. **System**: Device name and online/offline status
2. **Battery**: Current battery % or "External Power" indicator with low voltage warning
3. **Storage**: Used disk space (GB) with progress bar
4. **Recordings**: Total clips recorded in session
5. **History**: Motion events detected in last 24 hours

### Main Sections
- **Live Camera Feed**: MJPEG stream from /api/stream endpoint (640x480 @ 30fps)
- **Emergency Button**: Large red SOS button with confirmation dialog
- **Recent Recordings Grid**: Thumbnail previews with date/time (auto-refreshes)
- **Footer Links**: Configure (Settings), Multi-cam, Logout

### Settings Page (/config)
- **System Integration**: WiFi and Bluetooth toggles
- **Email Alerts**: SMTP configuration with test button (planned)
- **Google Drive**: Folder ID configuration
- **Save & Persist**: All settings saved to config.json

---

## 🔐 Security & Encryption

### Fernet Encryption
- **Algorithm**: Fernet (AES-128 with HMAC authentication)
- **Key Storage**: `config/storage_key.key` (auto-generated, keep backed up)
- **Pipeline**: Recording finalized → Encrypted → Plaintext deleted
- **Default**: Encryption enabled (toggle in first-run setup)

### Authentication
- **PIN-Based**: Default `1234` (changeable in setup)
- **Session**: Flask secret_key with secure cookies
- **Auth-Gated**: All /api and /config routes require login

---

## 🔋 Battery & Power Detection

### USB Power Bank Detection
- **Method**: `vcgencmd get_throttled` checks for undervoltage flag (bit 0x1)
- **External Power**: If no undervoltage detected, "External Power" shown in header
- **Battery %**: Optional config override for manual percentage
- **Low Voltage**: Red warning in Battery status card when undershooting

### Configuration
```json
{
  "battery": { "percent": 85 },  // Optional: override % when no HAT
  "storage": { "encrypt": true }  // Encryption enabled by default
}
```

---

## ⚙️ API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/login` | POST | - | PIN authentication |
| `/` | GET | ✓ | Dashboard (renders with live data) |
| `/config` | GET/POST | ✓ | Settings page (email, Google Drive, etc) |
| `/logout` | GET | ✓ | Clear session and redirect |
| `/api/status` | GET | ✓ | JSON: `{active, timestamp}` |
| `/api/stream` | GET | ✓ | MJPEG video stream (640x480 @30fps) |
| `/api/trigger_emergency` | POST | ✓ | Log emergency contact |

---

## 📊 Configuration Schema

```json
{
  "device_name": "ME_CAM_1",           // Display name
  "pin_code": "1234",                  // Login PIN
  "emergency_phone": "+1-800-...",     // Emergency contact
  "wifi_enabled": false,               // WiFi config toggle
  "bluetooth_enabled": false,          // Bluetooth toggle
  
  "email": {
    "enabled": false,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@gmail.com",
    "password": "app-password",
    "from_address": "alerts@safehome.local",
    "to_address": "recipient@example.com"
  },
  
  "google_drive": {
    "enabled": false,
    "folder_id": "1A2B3C4D5E6F7G"
  },
  
  "storage": {
    "recordings_dir": "recordings",
    "retention_days": 7,
    "motion_only": true,
    "encrypt": true,
    "encrypted_dir": "recordings_encrypted"
  },
  
  "detection": {
    "person_only": true,
    "sensitivity": 0.6,
    "min_motion_area": 500
  },
  
  "notifications": {
    "email_on_motion": false,
    "gdrive_on_motion": false,
    "webhook_on_motion": false,
    "webhook_url": ""
  },
  
  "first_run_completed": true
}
```

---

## 🛠️ Common Tasks

### Monitor System
```bash
# Watch service logs in real-time:
sudo journalctl -u mecamera.service -f

# View last 50 log lines:
sudo journalctl -u mecamera.service -n 50
```

### Change PIN
1. Edit config: `nano ~/ME_CAM/config/config.json`
2. Change `"pin_code"`: `"1234"` → your new PIN
3. Restart: `sudo systemctl restart mecamera.service`

### View Recordings
```bash
# Plaintext:
ls -lh ~/ME_CAM/recordings/

# Encrypted:
ls -lh ~/ME_CAM/recordings_encrypted/

# Via web:
http://<pi-ip>:8080/ → Recent Recordings grid
```

### Enable Email Alerts
1. Dashboard → ⚙️ Settings
2. Check "Enable Email Alerts"
3. Fill SMTP details (Gmail example: smtp.gmail.com:587 + app password)
4. Click "💾 Save Settings"

### Reset to Defaults
```bash
rm ~/ME_CAM/config/config.json
python3 -c "from config_manager import get_config; get_config()"
# Re-run first-run setup at http://<pi-ip>:8080/setup
```

---

## 🐛 Troubleshooting

### Dashboard Not Loading
**Check**: Service running and camera detected
```bash
sudo systemctl status mecamera.service
libcamera-hello --list-cameras
```

### No Recordings
**Check**: Motion detection enabled and sensitivity tuned
```bash
# Verify config:
grep "detection" ~/ME_CAM/config/config.json

# Test motion: wave hand in front of camera
# Should see clip in: ~/ME_CAM/recordings/
```

### No Thumbnails
**Check**: OpenCV installed and thumbnails directory writable
```bash
ls -ld ~/ME_CAM/web/static/thumbs/
python3 -c "import cv2; print(cv2.__version__)"
```

### Stream Endpoint Error
**Check**: Camera not in use by another process
```bash
ps aux | grep python
# Ensure only one main.py running
```

For complete troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting)

---

## 📦 Dependencies

- **Python 3.9+**
- **opencv-python**: Video capture & thumbnail generation
- **flask**: Web server & templating
- **cryptography**: Fernet encryption
- **loguru**: Structured logging
- **scipy** (optional): Advanced motion detection

Install all:
```bash
pip3 install -r requirements.txt
```

---

## 🔄 Systemd Service

Auto-start on boot:
```bash
sudo systemctl enable mecamera.service
sudo systemctl start mecamera.service
sudo systemctl status mecamera.service
```

Logs:
```bash
sudo journalctl -u mecamera.service -f
```

---

## 📄 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Complete setup guide with Pi OS configuration
- **[FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md)**: Implementation status and QA tests
- **[README.md](README.md)**: This file

---

## 🔜 Planned Features

- [ ] HLS streaming (better mobile support)
- [ ] Cloud sync with recovery
- [ ] Mobile app (iOS/Android)
- [ ] Advanced ML models (YOLO, TensorFlow)
- [ ] Two-factor authentication
- [ ] Snapshots on demand
- [ ] Video playback/trimming in web UI
- [ ] Push notifications
- [ ] Scheduled recording modes

---

## 📝 License

See [LICENSE](LICENSE) file

---

## 🤝 Support

For issues or feature requests:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) troubleshooting section
2. Review service logs: `sudo journalctl -u mecamera.service -f`
3. Check application logs: `tail -f ~/ME_CAM/logs/*.log`

---

**Version**: 1.0 Final (Thumbnails, Live Stream, Settings)
**Last Updated**: 2024
**Status**: Production Ready ✅
