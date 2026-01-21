# ME_CAM Installation Guide (Updated Jan 2026)

## ⚠️ IMPORTANT - READ FIRST
**DO NOT use Bullseye** — repos are archived and broken. Use **Bookworm (Latest OS)**.

## Prerequisites
- **Raspberry Pi Zero 2W** (or Pi 4/5) with imx708 camera
- **Raspberry Pi OS Lite (Bookworm 64-bit)** — Latest version
- Network connectivity (WiFi or Ethernet)
- Minimum 4GB SD card

---

## 5-Minute Quick Install

### 1. Flash SD Card with Raspberry Pi Imager

**Critical steps:**
1. Open **Raspberry Pi Imager**
2. **Choose OS:** Raspberry Pi OS Lite (64-bit) — **Latest (Bookworm)**
3. Click **gear icon** (Advanced Options):
   - ✅ Enable SSH → Use password auth
   - Set hostname: `mecamera` (or your device name)
   - Set username: `pi`
   - Set password: `raspberry` (change later)
   - Configure WiFi if needed
4. Select SD card → **Flash**

### 2. SSH into Pi
```bash
ssh pi@mecamera.local
# Password: raspberry
```

### 3. Update & Install System Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-dev build-essential python3-numpy python3-pil
```

### 4. Clone & Install ME_CAM
```bash
cd ~
git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV.git
cd ME_CAM-DEV
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade setuptools wheel
pip install Flask==3.0.0 Werkzeug==3.0.0 cryptography==41.0.0 qrcode[pil]==7.4.2 \
  psutil==5.9.5 yagmail==0.15.293 pydrive2==1.19.0 loguru==0.7.2
```

### 5. Verify Installation
```bash
python -c "import numpy, flask, PIL, cryptography, loguru; print('✓ All imports OK')"
```

### 5. Configure Camera & GPU Memory for Pi Zero 2W
```bash
# CRITICAL: Pi Zero 2W only has 512MB RAM total
# Set GPU memory to 128MB (NOT 512!)
echo "gpu_mem=128" | sudo tee -a /boot/config.txt
echo "dtoverlay=imx708" | sudo tee -a /boot/config.txt
sudo usermod -aG video pi
# DO NOT REBOOT YET - finish setup first
```

### 6. Clone Repository
```bash
cd ~
git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM.git
cd ME_CAM
```

### 7. Set Up Systemd Service
```bash
# Create service file
sudo tee /etc/systemd/system/mecamera.service > /dev/null << 'EOF'
[Unit]
Description=ME_CAM Security Camera System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ME_CAM
ExecStart=/usr/bin/python3 /home/pi/ME_CAM/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable mecamera.service
```

### 8. Lower Camera Resolution for Pi Zero 2W
```bash
# Edit libcamera_streamer.py to use 1280x720 instead of default
sed -i 's/"--width", "640"/"--width", "1280"/; s/"--height", "480"/"--height", "720"/' ~/ME_CAM/libcamera_streamer.py
```

### 9. Reboot & Start
```bash
sudo reboot
```

After reboot, SSH back in and start service:
```bash
sudo systemctl start mecamera.service
sudo systemctl status mecamera.service
```

### 10. Verify Installation
```bash
# Check service status
sudo systemctl status mecamera.service

# Check web server
curl http://localhost:8080/

# View logs
sudo journalctl -u mecamera.service -f
```

## First-Time Setup

1. Access the web interface at `http://raspberrypi.local:8080` or `http://<PI_IP>:8080`
2. You'll see the first-run setup screen with QR code
3. Create your first user account:
   - Default admin: username `admin`, password `admin123`
   - Or register a new account at `/register`

## Configuration

Edit `config/config_default.json` to configure:
- Device name
- Emergency contact
- Storage settings
- Email/Google Drive notifications
- Motion detection sensitivity

## Troubleshooting

### Service won't start
```bash
# Check logs for errors
sudo journalctl -u mecamera.service -n 50

# Common issues:
# - Missing Python packages: pip install <package>
# - Camera not detected: vcgencmd get_camera
# - Port already in use: sudo lsof -i :8080
```

### Camera not working
```bash
# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable

# Test camera
libcamera-still -o test.jpg
```

### Can't access web interface
```bash
# Find Pi IP address
hostname -I

# Test locally on Pi
curl http://localhost:8080/api/status

# Check firewall (if enabled)
sudo ufw allow 8080
```

## Security Recommendations

1. **Change default password**: `passwd`
2. **Change admin credentials**: Login and create a new user, delete default admin
3. **Enable firewall**:
   ```bash
   sudo apt install ufw
   sudo ufw allow 22
   sudo ufw allow 8080
   sudo ufw enable
   ```
4. **Update regularly**:
   ```bash
   sudo apt update && sudo apt upgrade
   cd ~/ME_CAM && git pull
   ```

## Updating

```bash
cd ~/ME_CAM
git pull
sudo systemctl restart mecamera.service
```

## Support

- GitHub: https://github.com/MangiafestoElectronicsLLC/ME_CAM
- Issues: https://github.com/MangiafestoElectronicsLLC/ME_CAM/issues
