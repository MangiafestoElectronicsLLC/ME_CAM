# ME_CAM Complete Deployment Guide for Raspberry Pi Zero 2W

**Professional step-by-step installation guide (Updated January 2026)**

---

## System Requirements

- **Hardware:**
  - Raspberry Pi Zero 2W (or Pi 4/5)
  - Compatible camera module (IMX708 recommended)
  - MicroSD card (8GB minimum, 16GB+ recommended)
  - Power supply (5V 2.5A minimum)
  
- **Software:**
  - Raspberry Pi OS Lite (Bookworm 64-bit) — **Latest version**
  - ⚠️ **DO NOT use Bullseye** — repositories are archived and broken

- **Network:**
  - WiFi or Ethernet connectivity
  - Access to router/network admin panel (for IP lookup)

---

## Part 1: Flash SD Card (5 minutes)

### Step 1: Download Raspberry Pi Imager
Download from: https://www.raspberrypi.com/software/

### Step 2: Select Operating System
1. Open Raspberry Pi Imager
2. Click **"Choose OS"**
3. Select **"Raspberry Pi OS (other)"**
4. Select **"Raspberry Pi OS Lite (64-bit)"** (Latest release)

### Step 3: Configure Advanced Options
Click the **gear icon ⚙️** in the bottom-right corner:

**Enable and configure:**
- ✅ **Set hostname:** `mecamera` (or your preferred name)
- ✅ **Enable SSH:** Use password authentication
- ✅ **Set username and password:**
  - Username: `pi`
  - Password: (your secure password)
- ✅ **Configure wireless LAN:** (if using WiFi)
  - SSID: Your WiFi network name
  - Password: Your WiFi password
  - Country: Your country code (e.g., `US`)
- ✅ **Set locale settings:**
  - Timezone: Your timezone
  - Keyboard layout: Your keyboard layout

### Step 4: Write to SD Card
1. Insert microSD card into your computer
2. Click **"Choose Storage"** and select your SD card
3. Click **"Write"**
4. Wait for completion (~5 minutes)
5. Safely eject SD card

---

## Part 2: Initial Boot & SSH Connection (2 minutes)

### Step 1: Boot Raspberry Pi
1. Insert SD card into Raspberry Pi
2. Connect power supply
3. Wait 1-2 minutes for first boot

### Step 2: Find Your Pi on Network

**Option A: Using hostname (if mDNS works)**
```bash
ssh pi@mecamera.local
```

**Option B: Using IP address**
1. Access your router's admin panel
2. Look for connected device named `mecamera` or similar
3. Note the IP address (e.g., `192.168.1.100`)
4. SSH using IP:
```bash
ssh pi@192.168.1.100
```

**First connection:**
- Type `yes` when asked to accept fingerprint
- Enter the password you set in Imager

---

## Part 3: System Setup (15 minutes)

Once connected via SSH, run these command blocks in order:

### Block 1: Update System & Install Core Dependencies
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-dev build-essential
```
⏱️ Takes ~10 minutes

### Block 2: Install System Libraries
```bash
sudo apt install -y python3-numpy python3-pil python3-opencv
```
⏱️ Takes ~2 minutes

**Why system packages?** On Pi Zero 2W, compiling numpy and opencv from source can take 30+ minutes each. System packages are pre-compiled and install instantly.

---

## Part 4: Install ME_CAM (5 minutes)

### Block 3: Clone Repository
```bash
cd ~
git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV.git
cd ME_CAM-DEV
```

### Block 4: Create Python Virtual Environment
```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade setuptools wheel
```

**Note:** The `--system-site-packages` flag allows the venv to access system-installed numpy, opencv, and Pillow.

### Block 5: Install Python Dependencies
```bash
pip install Flask==3.0.0 Werkzeug==3.0.0 cryptography==41.0.0 \
  qrcode[pil]==7.4.2 psutil==5.9.5 yagmail==0.15.293 \
  pydrive2==1.19.0 loguru==0.7.2
```
⏱️ Takes ~3 minutes

### Block 6: Verify Installation
```bash
python -c "import numpy, flask, PIL, cryptography, loguru, cv2; print('✓ All dependencies OK')"
```

**Expected output:** `✓ All dependencies OK`

---

## Part 5: Configure Camera (3 minutes)

### Step 1: Run raspi-config
```bash
sudo raspi-config
```

### Step 2: Enable Camera
1. Select: **3 Interface Options**
2. Select: **I1 Legacy Camera**
   - Choose: **NO** (disable legacy camera support)
3. Select: **P1 Camera**
   - Choose: **YES** (enable libcamera)
4. Select: **I5 I2C**
   - Choose: **YES** (enable I2C)
5. Select **Finish**
6. Select **Yes** to reboot

**The Pi will reboot now. Wait 1 minute.**

---

## Part 6: Launch ME_CAM

### Step 1: Reconnect via SSH
```bash
ssh pi@mecamera.local
# Or: ssh pi@<your-pi-ip>
```

### Step 2: Start ME_CAM
```bash
cd ~/ME_CAM-DEV
source venv/bin/activate
python main.py
```

**Expected output:**
```
[INFO] ME_CAM Starting...
[INFO] Camera initialized
[INFO] Web server running on port 8080
```

### Step 3: Access Web Dashboard
Open a web browser and navigate to:
```
http://mecamera.local:8080
```

Or using IP address:
```
http://192.168.1.100:8080
```

---

## Part 7: Optional - Auto-Start on Boot

To make ME_CAM start automatically when the Pi boots:

```bash
sudo tee /etc/systemd/system/mecamera.service > /dev/null << 'EOF'
[Unit]
Description=ME_CAM Security Camera System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ME_CAM-DEV
ExecStart=/home/pi/ME_CAM-DEV/venv/bin/python /home/pi/ME_CAM-DEV/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mecamera
sudo systemctl start mecamera
```

**Check service status:**
```bash
sudo systemctl status mecamera
```

**View live logs:**
```bash
sudo journalctl -u mecamera -f
```

---

## Troubleshooting

### Cannot SSH - "Connection refused"
**Cause:** SSH wasn't enabled during imaging  
**Fix:** Re-flash SD card and ensure SSH is enabled in Imager settings

### Cannot reach mecamera.local
**Cause:** mDNS not working on your network/OS  
**Fix:** Use IP address instead of hostname

### "ModuleNotFoundError: No module named 'cv2'"
**Cause:** opencv not installed  
**Fix:**
```bash
sudo apt install -y python3-opencv
```

### "ModuleNotFoundError: No module named 'numpy'" or "PIL"
**Cause:** System packages not installed  
**Fix:**
```bash
sudo apt install -y python3-numpy python3-pil
```

### pip install hangs or takes forever
**Cause:** Trying to compile numpy/opencv from source  
**Fix:** Make sure you installed system packages first (Block 2)

### "git: command not found"
**Cause:** Git not installed (Bookworm Lite doesn't include it)  
**Fix:**
```bash
sudo apt install -y git
```

### Camera not detected
**Cause:** Camera not enabled or not connected properly  
**Fix:**
1. Check physical camera connection
2. Run `raspi-config` and enable camera
3. Verify with: `libcamera-hello --list-cameras`

---

## Quick Command Reference

### Start ME_CAM (manual)
```bash
cd ~/ME_CAM-DEV
source venv/bin/activate
python main.py
```

### Stop ME_CAM (if running manually)
Press `Ctrl+C` in the terminal

### Check service status (if using systemd)
```bash
sudo systemctl status mecamera
```

### Restart service
```bash
sudo systemctl restart mecamera
```

### View logs
```bash
sudo journalctl -u mecamera -f
```

### Update ME_CAM code
```bash
cd ~/ME_CAM-DEV
git pull origin main
sudo systemctl restart mecamera  # If using service
```

### Reboot Pi
```bash
sudo reboot
```

### Shutdown Pi
```bash
sudo shutdown -h now
```

---

## Total Time Required

| Step | Duration |
|------|----------|
| Flash SD card | 5 min |
| First boot | 2 min |
| System update | 10 min |
| Install dependencies | 5 min |
| Clone & setup | 3 min |
| Configure camera | 3 min |
| **Total** | **~28 minutes** |

---

## Why This Guide Works (vs. Older Guides)

| Issue | Old Approach (Bullseye) | This Guide (Bookworm) |
|-------|------------------------|----------------------|
| OS repos | Archived, broken | Active, maintained |
| Python version | 3.9 (old) | 3.13 (modern) |
| numpy install | 30+ min compile | Instant (system pkg) |
| Pillow install | 20+ min compile | Instant (system pkg) |
| opencv install | 60+ min compile | Instant (system pkg) |
| git availability | Pre-installed | Must install |

**Key insight:** Use system packages for heavy C libraries (numpy, opencv, Pillow), use pip for pure Python packages (Flask, loguru, etc.)

---

## Support & Resources

- **Project Repository:** https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV
- **Issues:** Open an issue on GitHub
- **Documentation:** See `README.md` and other guides in the repository

---

## License

See LICENSE file in repository
