# Pi Zero 2W Complete Setup Guide (Flash to Auto-Boot)

## STEP 1: Flash SD Card with Raspberry Pi Imager

### Download Raspberry Pi Imager
- Windows: https://www.raspberrypi.com/software/
- Or install via: `winget install RaspberryPi.Imager`

### Flash Process (Detailed)

1. **Launch Raspberry Pi Imager**

2. **Choose Device:**
   - Click "Choose Device"
   - Select: **Raspberry Pi Zero 2 W**

3. **Choose OS:**
   - Click "Choose OS"
   - Select: **Raspberry Pi OS (64-bit)** *(Recommended)*
   - *Note: Full OS, not Lite - we need picamera2 support*

4. **Choose Storage:**
   - Insert SD card (16GB+ recommended)
   - Click "Choose Storage"
   - Select your SD card

5. **Configure Settings (CRITICAL):**
   - Click "⚙️ Edit Settings" button (or it will auto-prompt)
   
   **GENERAL Tab:**
   - ✅ Set hostname: `mecamdev2` (or your choice)
   - ✅ Set username: `pi`
   - ✅ Set password: `raspberry` (or secure password)
   - ✅ Configure wireless LAN:
     - SSID: `[Your WiFi Name]`
     - Password: `[Your WiFi Password]`
     - Country: `US` (or your country)
   - ✅ Set locale: Your timezone (e.g., `America/New_York`)
   
   **SERVICES Tab:**
   - ✅ **Enable SSH**
   - Select: "Use password authentication"
   
   **OPTIONS Tab:**
   - ✅ Play sound when complete (optional)

6. **Write to SD Card:**
   - Click "SAVE"
   - Click "YES" to apply settings
   - Click "YES" to confirm erase
   - Wait 5-10 minutes

7. **Insert SD Card & Boot Pi:**
   - Remove SD card from computer
   - Insert into Pi Zero 2W
   - Power on Pi
   - **Wait 2-3 minutes** for first boot

---

## STEP 2: Connect via SSH

### Find Your Pi

**Option A - Using Hostname (if mDNS works):**
```powershell
ssh pi@mecamdev2.local
```

**Option B - Using IP Address:**
```powershell
# On your router's admin page, find device named "mecamdev2"
# Or use network scanner
ssh pi@10.2.1.X
```

**Option C - Scan Network:**
```powershell
arp -a | findstr "b8-27-eb dc-a6-32"
# Pi MAC addresses start with b8:27:eb or dc:a6:32
```

Password: `raspberry` (or what you set)

---

## STEP 3: Install ME_CAM (One Command)

**Copy/paste this entire block:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies (includes picamera2)
sudo apt install -y git python3-dev build-essential \
  python3-numpy python3-pil python3-opencv \
  python3-picamera2 libcamera-apps

# Clone ME_CAM
cd ~
git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV.git
cd ME_CAM-DEV

# Create venv with system packages access
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install Python packages (NOT numpy/opencv - using system versions)
pip install Flask==3.0.0 Werkzeug==3.0.0 cryptography==41.0.0 \
  qrcode[pil]==7.4.2 psutil==5.9.5 yagmail==0.15.293 \
  pydrive2==1.19.0 loguru==0.7.2

# Verify installation
python -c "import numpy, flask, PIL, cv2, loguru; print('✓ All packages OK')"

echo ""
echo "✓ Installation complete!"
echo "Next: Test manually then setup auto-boot"
```

This takes **10-15 minutes** on Pi Zero 2W.

---

## STEP 4: Test ME_CAM (Before Auto-Boot)

### Manual Test (Important!)

```bash
cd ~/ME_CAM-DEV
source venv/bin/activate

# For Pi Zero 2W, MUST use lite mode
python main_lite.py
```

**What to look for:**
- ✅ `[PI_DETECT] Detected: Raspberry Pi Zero 2W`
- ✅ `[PI_DETECT] RAM: 512MB`
- ✅ `[PI_DETECT] Camera mode: lite`
- ✅ `Running on http://10.2.1.X:8080`

**Test in browser:** `http://10.2.1.X:8080`

- Should show **"LITE MODE V2.1-LITE"** badge
- Camera feed should work
- Dashboard should load

**Press Ctrl+C** to stop after verifying.

---

## STEP 5: Setup Auto-Boot (Systemd Service)

### Create Auto-Detection Startup Script

```bash
cd ~/ME_CAM-DEV

# Create smart launcher script
cat > start_mecam.sh << 'EOF'
#!/bin/bash
# Auto-detect Pi model and launch appropriate mode

PROJECT_DIR="/home/pi/ME_CAM-DEV"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

cd "$PROJECT_DIR"

# Detect Pi model from device tree
MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")

if echo "$MODEL" | grep -qi "Pi Zero 2"; then
    echo "[STARTUP] Detected Pi Zero 2W - Launching LITE MODE"
    exec "$VENV_PYTHON" main_lite.py
elif echo "$MODEL" | grep -qi "Pi 3\|Pi 4\|Pi 5"; then
    echo "[STARTUP] Detected Pi 3/4/5 - Launching REGULAR MODE"
    exec "$VENV_PYTHON" main.py
else
    echo "[STARTUP] Unknown Pi model: $MODEL"
    echo "[STARTUP] Defaulting to auto-detection mode"
    exec "$VENV_PYTHON" main.py
fi
EOF

# Make executable
chmod +x start_mecam.sh

# Test the script
./start_mecam.sh
# Should launch correctly - press Ctrl+C to stop
```

### Create Systemd Service

```bash
sudo nano /etc/systemd/system/mecam.service
```

**Paste this:**

```ini
[Unit]
Description=ME_CAM Auto-Detect Mode (Pi Zero/3/4/5)
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ME_CAM-DEV
Environment="PATH=/home/pi/ME_CAM-DEV/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/ME_CAM-DEV/start_mecam.sh
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/ME_CAM-DEV/logs/mecam.log
StandardError=append:/home/pi/ME_CAM-DEV/logs/mecam.log

[Install]
WantedBy=multi-user.target
```

**Save:** `Ctrl+X`, `Y`, `Enter`

### Enable and Start Service

```bash
# Create logs directory
mkdir -p ~/ME_CAM-DEV/logs

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable mecam

# Start service now
sudo systemctl start mecam

# Check status
sudo systemctl status mecam

# View logs
tail -30 ~/ME_CAM-DEV/logs/mecam.log
```

**Look for:**
- ✅ `[STARTUP] Detected Pi Zero 2W - Launching LITE MODE`
- ✅ `[PI_DETECT] Camera mode: lite`
- ✅ Service shows `active (running)`

---

## STEP 6: Test Auto-Boot

```bash
# Reboot Pi
sudo reboot
```

**Wait 60-90 seconds**, then:

1. **SSH back in:** `ssh pi@mecamdev2.local`
2. **Check service:** `sudo systemctl status mecam`
3. **Check logs:** `tail -30 ~/ME_CAM-DEV/logs/mecam.log`
4. **Test web:** Open browser to `http://10.2.1.X:8080`

✅ **Success:** Dashboard loads with "LITE MODE" badge and live camera feed.

---

## Quick Management Commands

```bash
# View live logs
tail -f ~/ME_CAM-DEV/logs/mecam.log

# Restart service (after code changes)
sudo systemctl restart mecam

# Stop service
sudo systemctl stop mecam

# Check status
sudo systemctl status mecam

# Disable auto-boot
sudo systemctl disable mecam

# Re-enable auto-boot
sudo systemctl enable mecam

# View last 50 journal entries
sudo journalctl -u mecam -n 50 --no-pager
```

---

## Hardware Detection Logic

| Pi Model | RAM | Mode Used | Entry Point |
|----------|-----|-----------|-------------|
| **Pi Zero 2W** | 512MB | **LITE** | `main_lite.py` |
| **Pi 3B/3B+** | 1GB | Regular | `main.py` |
| **Pi 4** | 2GB+ | Regular | `main.py` |
| **Pi 5** | 4GB+ | Regular | `main.py` |

**The startup script automatically detects your Pi model and chooses the right mode.**

---

## Troubleshooting

### "git: command not found"
```bash
sudo apt install -y git
```

### "pip install" hangs compiling numpy
**Fix:** You skipped step to install `python3-numpy` via apt.
```bash
sudo apt install -y python3-numpy python3-pil
```

### SSH "Connection refused"
SSH wasn't enabled during flash. Re-flash with SSH enabled in Imager settings.

### Can't reach `mecamera.local`
Use IP address instead:
```bash
# On Pi, find IP:
hostname -I

# SSH from Windows:
ssh pi@<IP_ADDRESS>
```

---

## Why This Works (vs Old Bullseye Guides)

| Issue | Old (Bullseye) | New (Bookworm) |
|-------|----------------|----------------|
| Repos | Archived, broken | Active, working |
| Python | 3.9 (old numpy) | 3.13 (modern) |
| numpy | Compiles 30+ min | System package (instant) |
| Pillow | Compiles 20+ min | System package (instant) |
| git | Not installed | Must install |

**Key difference:** Use system packages for heavy C libraries (numpy, Pillow), pip for pure Python.
