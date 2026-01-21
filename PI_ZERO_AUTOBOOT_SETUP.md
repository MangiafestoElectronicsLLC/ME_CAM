# Pi Zero 2W Auto-Boot Setup Guide
**Complete setup from current state to auto-starting ME_CAM in lite mode**

---

## STEP 1: Finish Installation (System Packages Method)

```bash
# You should already be in ~/ME_CAM-DEV with venv activated
# If not: cd ~/ME_CAM-DEV && source venv/bin/activate

# 1. Recreate venv with system packages access
deactivate
rm -rf venv
python3 -m venv venv --system-site-packages

# 2. Install system packages (skip if already done)
sudo apt install -y python3-numpy python3-pil python3-opencv git

# 3. Activate new venv
source venv/bin/activate

# 4. Verify system packages work
python -c "import numpy, PIL, cv2; print('✓ System packages OK')"

# 5. Install ONLY pure Python packages (NOT numpy/Pillow)
pip install Flask==3.0.0 Werkzeug==3.0.0 cryptography==41.0.0 qrcode[pil]==7.4.2 psutil==5.9.5 yagmail==0.15.293 pydrive2==1.19.0 loguru==0.7.2

# 6. Test ME_CAM works
python main.py
# Press Ctrl+C after you see it start successfully
```

---

## STEP 2: Create Systemd Service for Auto-Boot

```bash
# Create service file
sudo nano /etc/systemd/system/mecam-lite.service
```

**Paste this content:**

```ini
[Unit]
Description=ME_CAM Lite Mode (Pi Zero 2W)
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ME_CAM-DEV
Environment="PATH=/home/pi/ME_CAM-DEV/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/pi/ME_CAM-DEV/venv/bin/python /home/pi/ME_CAM-DEV/main.py
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/ME_CAM-DEV/logs/mecam_lite.log
StandardError=append:/home/pi/ME_CAM-DEV/logs/mecam_lite.log

[Install]
WantedBy=multi-user.target
```

**Save:** `Ctrl+X`, then `Y`, then `Enter`

```bash
# Create logs directory if it doesn't exist
mkdir -p ~/ME_CAM-DEV/logs

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable mecam-lite
sudo systemctl start mecam-lite

# Check status
sudo systemctl status mecam-lite
```

---

## STEP 3: Configure Hostname (Already Done!)

You already set hostname to **MECAMDEV2**, so you can access via:
- IP: `http://10.2.1.2:8080`
- Hostname: `http://MECAMDEV2.local:8080` (if mDNS works on Windows)
- Hostname: `http://MECAMDEV2:8080` (might work on local network)

**To verify hostname:**
```bash
hostname
# Should show: MECAMDEV2
```

---

## STEP 4: Verify Everything Works

```bash
# 1. Check service is running
sudo systemctl is-active mecam-lite

# 2. Check logs (last 30 lines)
tail -30 ~/ME_CAM-DEV/logs/mecam_lite.log

# 3. Test API endpoints
curl -s http://localhost:8080/api/status | python3 -m json.tool

# 4. Check if it detected Pi Zero 2W and lite mode
grep "Pi Zero 2W" ~/ME_CAM-DEV/logs/mecam_lite.log
grep "lite" ~/ME_CAM-DEV/logs/mecam_lite.log
```

---

## STEP 5: Test Auto-Boot

```bash
# Reboot the Pi
sudo reboot
```

**After reboot (wait 60 seconds), from Windows:**

1. SSH back in: `ssh pi@10.2.1.2`
2. Check service: `sudo systemctl status mecam-lite`
3. Check logs: `tail -30 ~/ME_CAM-DEV/logs/mecam_lite.log`
4. Test web: Open browser to `http://10.2.1.2:8080`

---

## STEP 6: Manage the Service

```bash
# Stop service
sudo systemctl stop mecam-lite

# Start service
sudo systemctl start mecam-lite

# Restart service (after code changes)
sudo systemctl restart mecam-lite

# View live logs
tail -f ~/ME_CAM-DEV/logs/mecam_lite.log

# Disable auto-boot
sudo systemctl disable mecam-lite

# Re-enable auto-boot
sudo systemctl enable mecam-lite
```

---

## Quick Health Check Command

```bash
# Run this anytime to check status
cd ~/ME_CAM-DEV && \
echo "=== Service Status ===" && \
systemctl is-active mecam-lite && \
echo "=== Last 10 Log Lines ===" && \
tail -10 logs/mecam_lite.log && \
echo "=== API Test ===" && \
curl -s http://localhost:8080/api/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Mode: {d.get(\"camera_mode\", \"N/A\")} | Uptime: {d.get(\"uptime\", \"N/A\")}s')"
```

---

## Network Access Summary

**Your Pi Zero 2W is accessible at:**

| Method | Address | Notes |
|--------|---------|-------|
| **IP Address** | `http://10.2.1.2:8080` | Always works |
| **Hostname (Local)** | `http://MECAMDEV2:8080` | May work on your network |
| **mDNS (macOS/Linux)** | `http://MECAMDEV2.local:8080` | Requires Bonjour on Windows |
| **SSH** | `ssh pi@10.2.1.2` | Remote management |

**Port:** 8080 (HTTP)

---

## Troubleshooting

### Service won't start
```bash
# Check detailed errors
sudo journalctl -u mecam-lite -n 50 --no-pager

# Check permissions
ls -la /home/pi/ME_CAM-DEV/main.py
ls -la /home/pi/ME_CAM-DEV/venv/bin/python

# Test manually
cd ~/ME_CAM-DEV
source venv/bin/activate
python main.py
```

### Camera not working
```bash
# Check camera detection
vcgencmd get_camera

# Should show: supported=1 detected=1

# Check permissions
sudo usermod -a -G video pi
```

### Can't access from Windows
```bash
# On Pi, check if service is listening
sudo netstat -tulpn | grep 8080

# Check firewall (if enabled)
sudo ufw status
sudo ufw allow 8080/tcp  # If firewall is active
```

### Wrong mode (not lite)
```bash
# Check detection in logs
grep -i "detected" ~/ME_CAM-DEV/logs/mecam_lite.log
grep -i "ram" ~/ME_CAM-DEV/logs/mecam_lite.log
grep -i "camera mode" ~/ME_CAM-DEV/logs/mecam_lite.log

# Should show: "Pi Zero 2W", "512MB", "lite mode"
```

---

## Success Checklist

- ✅ Venv created with `--system-site-packages`
- ✅ System packages installed (numpy, opencv, PIL)
- ✅ Pure Python packages installed via pip
- ✅ ME_CAM runs manually without errors
- ✅ Systemd service created at `/etc/systemd/system/mecam-lite.service`
- ✅ Service enabled: `sudo systemctl enable mecam-lite`
- ✅ Service running: `sudo systemctl status mecam-lite`
- ✅ Logs show "Pi Zero 2W" and "lite mode"
- ✅ Web dashboard accessible at `http://10.2.1.2:8080`
- ✅ Survives reboot (auto-starts)
- ✅ Hostname set to MECAMDEV2

**You're done when all checkboxes are ✅!**
