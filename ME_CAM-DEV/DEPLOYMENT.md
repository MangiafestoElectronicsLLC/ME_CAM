# ME_CAM Deployment Guide

## Overview
This document covers deploying the ME_CAM security system to your Raspberry Pi Zero 2 W with ArduCAM and USB power bank.

## Prerequisites
- Raspberry Pi Zero 2 W running Raspberry Pi OS Bullseye or later
- ArduCAM USB camera module
- External USB power bank
- Network connection (WiFi via USB adapter or Ethernet)
- SSH access to Pi (default user: `pi`, password: `raspberry`)

---

## Phase 1: Fresh Pi Setup (One-Time)

### 1.1 Flash SD Card
- Download Raspberry Pi Imager from https://www.raspberrypi.com/software/
- Insert SD card and flash with **Raspberry Pi OS Lite (32-bit)**
- During flash, set hostname, username/password, and WiFi details in Advanced Options

### 1.2 Connect Pi and Enable SSH
```bash
ssh pi@<pi-ip>
# Default: pi@raspberrypi.local
```

### 1.3 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-dev libatlas-base-dev libjasper-dev libtiff5 \
    libjasper1 libharfbuzz0b libwebp6 libopenjp2-7 libopenjp2-7-dev \
    libopenjpip7 libtiff5 libharfbuzz0b libwebp6 python3-opencv
```

### 1.4 Install Python Dependencies
```bash
pip3 install --upgrade pip
pip3 install cryptography opencv-python loguru flask
```

### 1.5 Enable Camera
```bash
sudo raspi-config
# Navigate to: Interfacing Options > Camera > Enable
# Reboot: sudo reboot
```

### 1.6 Verify Camera
```bash
libcamera-hello --list-cameras
# Should list your ArduCAM module
```

---

## Phase 2: Deploy ME_CAM Code

### 2.1 Upload Files to Pi
From your Windows machine, copy the project to Pi:
```powershell
# In PowerShell:
scp -r "C:\Users\nickp\Downloads\ME_CAM-DEV\ME_CAM-DEV" pi@<pi-ip>:~/ME_CAM
```

Or manually via SSH:
```bash
ssh pi@<pi-ip>
mkdir -p ~/ME_CAM
# Then copy files via SCP or paste code directly
```

### 2.2 Initialize Configuration
```bash
cd ~/ME_CAM
python3 -c "from config_manager import get_config; get_config()"
# This creates config/config.json from config_default.json
```

### 2.3 Create Required Directories
```bash
mkdir -p ~/ME_CAM/recordings
mkdir -p ~/ME_CAM/recordings_encrypted
mkdir -p ~/ME_CAM/web/static/thumbs
mkdir -p ~/ME_CAM/logs
```

### 2.4 Test Run
```bash
cd ~/ME_CAM
python3 main.py
# Should start on 0.0.0.0:8080
# Open browser to http://<pi-ip>:8080
# Default PIN: 1234
```

If successful, **Ctrl+C** to stop.

---

## Phase 3: First-Run Setup (Web UI)

### 3.1 Access Dashboard
1. Open http://<pi-ip>:8080 in your browser
2. Enter PIN: **1234**
3. Click "First Run Setup" or navigate to /setup

### 3.2 Configure Basics
- **Device Name**: Your camera's friendly name (e.g., "Front Door")
- **PIN Code**: Change from default 1234 to your secure PIN
- **Emergency Phone**: Contact number for emergency alerts

### 3.3 Storage Settings
- **Retention**: Days to keep recordings (default 7)
- **Motion Only**: Record only on motion (recommended)
- **Encryption**: ENABLED by default (✓) for secure local storage

### 3.4 Detection
- **Person Only**: Detect humans (not just any motion)
- **Sensitivity**: 0.6 for balanced detection
- **Min Motion Area**: 500 pixels minimum change

### 3.5 Optional: Email Alerts
Navigate to **⚙️ Settings** page and enable:
- **Email Notifications**: ON
- **SMTP Server**: smtp.gmail.com (for Gmail)
- **SMTP Port**: 587
- **Username**: your-email@gmail.com
- **Password**: Your Gmail app-specific password
- **From Address**: alerts@safehome.local
- **Alert Recipient**: your-email@gmail.com

### 3.6 Optional: Google Drive Backup
- **Enable Google Drive Backup**: ON
- **Folder ID**: Create a folder in Google Drive, open it, copy ID from URL
  - Example URL: `https://drive.google.com/drive/folders/1A2B3C4D5E6F7G`
  - ID is: `1A2B3C4D5E6F7G`

---

## Phase 4: Systemd Service Setup (Persistent)

### 4.1 Enable Auto-Start
```bash
sudo nano /etc/systemd/system/mecamera.service
```

Paste (or copy from `etc/systemd/system/mecamera.service`):
```ini
[Unit]
Description=ME_CAM Security Camera System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ME_CAM
ExecStart=/usr/bin/python3 /home/pi/ME_CAM/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.2 Enable Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable mecamera.service
sudo systemctl start mecamera.service
sudo systemctl status mecamera.service
```

### 4.3 View Logs
```bash
sudo journalctl -u mecamera.service -f
# Press Ctrl+C to exit
```

---

## Phase 5: Feature Verification

### 5.1 Dashboard Access
- Open http://<pi-ip>:8080/login
- Login with your PIN
- Should see 5-card status grid with System, Battery, Storage, Recordings, History

### 5.2 Live Stream (Optional)
- Embedded in dashboard (click camera section)
- Direct stream: http://<pi-ip>:8080/api/stream (MJPEG format)

### 5.3 Battery Monitoring
- **Header**: Shows battery % or "External Power"
- **Low Voltage Warning**: Red alert if undershooting (vcgencmd detection)
- **USB Power Bank**: Detected automatically

### 5.4 Recording Status
- Motion clips auto-saved to ~/ME_CAM/recordings/
- Encrypted clips in ~/ME_CAM/recordings_encrypted/ (when enabled)
- Thumbnails generated in ~/ME_CAM/web/static/thumbs/

### 5.5 Settings Page
- Navigate to ⚙️ Settings
- Toggle optional integrations (Email, Google Drive, WiFi, Bluetooth)
- Fill in credentials
- Click "💾 Save Settings"
- Settings persist across restarts

---

## Common Tasks

### Monitor In Real-Time
```bash
# On Pi:
sudo journalctl -u mecamera.service -f

# Or tail logs:
tail -f ~/ME_CAM/logs/*.log
```

### View Recordings
```bash
# SSH to Pi and list:
ls -lah ~/ME_CAM/recordings/
ls -lah ~/ME_CAM/recordings_encrypted/

# Or via web dashboard:
http://<pi-ip>:8080/ → Recent Recordings grid
```

### Test Motion Detection
```bash
# Wave hand in front of camera
# Should see clip appear in ~/ME_CAM/recordings/
# Within ~10 seconds
```

### Change PIN
1. Stop service: `sudo systemctl stop mecamera.service`
2. Edit config:
   ```bash
   nano ~/ME_CAM/config/config.json
   # Change "pin_code": "1234" to your new PIN
   ```
3. Restart: `sudo systemctl start mecamera.service`

### Restore to Defaults
```bash
# Backup current config:
cp ~/ME_CAM/config/config.json ~/ME_CAM/config/config.json.bak

# Reset to defaults:
rm ~/ME_CAM/config/config.json
python3 -c "from config_manager import get_config; get_config()"

# Re-run first-run setup at http://<pi-ip>:8080/setup
```

### Free Up Storage
```bash
# Delete old recordings (older than 7 days):
find ~/ME_CAM/recordings/ -mtime +7 -delete
find ~/ME_CAM/recordings_encrypted/ -mtime +7 -delete

# Clear thumbnails:
rm ~/ME_CAM/web/static/thumbs/*
```

---

## Troubleshooting

### Dashboard Shows "Camera Unavailable"
**Cause**: Camera not detected or OpenCV error
**Fix**:
1. Verify camera: `libcamera-hello --list-cameras`
2. Check permissions: `ls -l /dev/video0`
3. Ensure arducam service running (if applicable)
4. Restart service: `sudo systemctl restart mecamera.service`

### Login Loop (Cannot Enter PIN)
**Cause**: PIN authentication failing or session issue
**Fix**:
1. Clear browser cookies
2. Verify PIN in config.json: `cat ~/ME_CAM/config/config.json | grep pin_code`
3. Try default PIN: `1234`

### Encryption Errors ("cannot deserialize key")
**Cause**: Corrupted storage_key.key or missing
**Fix**:
1. Check key exists: `ls ~/ME_CAM/config/storage_key.key`
2. Backup and regenerate: `rm ~/ME_CAM/config/storage_key.key` (new key generated on next run)
3. Old encrypted files become unreadable; back up if needed

### No Recordings
**Cause**: Motion not detected or storage disabled
**Fix**:
1. Verify detection enabled: `grep "detection" ~/ME_CAM/config/config.json`
2. Test motion: Wave hand in front of camera
3. Check sensitivity: Dashboard → Settings → Detection (lower = more sensitive)
4. Verify storage path exists: `ls -ld ~/ME_CAM/recordings/`

### High CPU Usage
**Cause**: Inefficient motion detection or multiple processes
**Fix**:
1. Lower sensitivity: Reduce `detection.sensitivity` in config
2. Increase `detection.min_motion_area` to ignore small changes
3. Enable `storage.motion_only` to skip continuous recording
4. Check running processes: `ps aux | grep python`

### No Thumbnails in Dashboard
**Cause**: OpenCV not processing videos or thumbnail dir not writable
**Fix**:
1. Verify thumbnails directory: `ls ~/ME_CAM/web/static/thumbs/`
2. Test thumbnail generation:
   ```bash
   cd ~/ME_CAM
   python3 -c "from thumbnail_gen import extract_thumbnail; extract_thumbnail('recordings/sample.mp4', 'web/static/thumbs')"
   ```
3. Check permissions: `ls -ld ~/ME_CAM/web/static/thumbs/`

---

## Updating Code

### Via SCP (Recommended)
```powershell
# On Windows:
scp -r "C:\Users\nickp\Downloads\ME_CAM-DEV\ME_CAM-DEV\*" pi@<pi-ip>:~/ME_CAM/
```

### Manual (Single File)
```bash
# On Pi:
nano ~/ME_CAM/web/app.py
# Paste new code, Ctrl+X → Y → Enter

# Restart:
sudo systemctl restart mecamera.service
```

### Verify Update
```bash
# Check code updated:
grep "version" ~/ME_CAM/main.py  # or look for your change

# Restart and check logs:
sudo systemctl restart mecamera.service
sudo journalctl -u mecamera.service -n 20
```

---

## Advanced: USB Power Bank Detection

The system automatically detects external power (USB power bank) via:
1. **vcgencmd get_throttled**: Checks for undervoltage flag (0x1)
   - If bit 0 is NOT set → External power assumed adequate
   - If set → Battery low warning shown
2. **Battery %**: Optional config override in `config.json`:
   ```json
   "battery": { "percent": 85 }
   ```

To manually set battery percentage (e.g., for testing):
```bash
nano ~/ME_CAM/config/config.json
# Add: "battery": { "percent": 75 }
```

---

## Support & Logs

### Accessing Logs on Pi
```bash
# Service logs (last 50 lines):
sudo journalctl -u mecamera.service -n 50

# Live tail:
sudo journalctl -u mecamera.service -f

# Detailed error:
grep "ERROR\|Exception" /home/pi/ME_CAM/logs/*.log
```

### Collecting Debug Info
```bash
# Create debug bundle:
tar -czf ~/ME_CAM_debug.tar.gz ~/ME_CAM/config ~/ME_CAM/logs
# Download to Windows for inspection
```

---

## Security Notes

1. **Always change default PIN** from `1234`
2. **Encryption enabled by default** — Recordings stored encrypted
3. **Storage key auto-generated** at `config/storage_key.key` — Keep backed up
4. **HTTPS not enabled** — Use only on trusted networks
5. **Email credentials** stored plaintext in config.json — Secure your Pi

---

## Next Steps

1. ✅ Deploy to Pi following Phases 1-4 above
2. ✅ Run first-run setup at http://<pi-ip>:8080/setup
3. ✅ Test motion detection by waving in front of camera
4. ✅ Configure optional integrations (Email, Google Drive)
5. ✅ Set up systemd service for auto-start
6. ✅ Monitor logs and verify stable operation for 24 hours

---

**Version**: 1.0 (Final with Thumbnails, Live Stream, Settings)
**Last Updated**: 2024
**Author**: ME_CAM Team
