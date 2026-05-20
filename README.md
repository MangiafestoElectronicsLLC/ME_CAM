# ME_CAM: Secure Raspberry Pi Camera & IoT Edge Computing Platform

**Professional-grade security camera system for Raspberry Pi with end-to-end encryption, zero-trust networking, and enterprise-class device management.**

[![Version Badge](https://img.shields.io/badge/version-3.0.0-0066cc.svg)](https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV/releases)
[![Python Support](https://img.shields.io/badge/python-3.9%2B-00aa00.svg)](https://www.python.org/downloads/)
[![Raspberry Pi Compatible](https://img.shields.io/badge/rpi-Zero%202W%20%2F%204%20%2F%205-cc0000.svg)](https://www.raspberrypi.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Security Scanning](https://img.shields.io/badge/security-checked-00cc00.svg)](SECURITY.md)
[![Test Coverage](https://img.shields.io/badge/tests-security--focused-0099ff.svg)](tests/)

## V3 highlights

- Security middleware with CSRF protection, rate limiting, and response hardening
- Password hashing and enrollment-key based device onboarding
- Pi Zero 2W aware lite deployment path
- Updated release hygiene checks to block lab artifacts from public releases
- New documentation for GitHub-based device installs and Replit-hosted dashboard flows
- Security-focused automated tests for auth, headers, CSRF, and rate limiting

## Recommended deployment model

- Use a fresh Raspberry Pi OS Lite 32-bit image for Pi Zero 2W deployments
- Use the lite runtime for constrained devices
- Treat local device repair scripts, wheel bundles, and result dumps as non-release artifacts

## Fresh SD Card Quick Setup

For a brand-new flashed microSD card, use this path:

1. Flash Raspberry Pi OS Lite (32-bit) using Raspberry Pi Imager.
2. Boot the Pi, connect to internet, and SSH in.
3. Run:

```bash
curl -sSL https://raw.githubusercontent.com/MangiafestoElectronicsLLC/ME_CAM-DEV/main/scripts/auto_setup_mecam.sh | bash
```

Optional non-interactive device number:

```bash
MECAM_DEVICE_NUMBER=3 curl -sSL https://raw.githubusercontent.com/MangiafestoElectronicsLLC/ME_CAM-DEV/main/scripts/auto_setup_mecam.sh | bash
```

Fully zero-prompt (device number, hostname, and WiFi):

```bash
MECAM_DEVICE_NUMBER=3 \
MECAM_HOSTNAME=mecamdev3 \
MECAM_WIFI_SSID='YourWifi' \
MECAM_WIFI_PASSWORD='YourPassword' \
curl -sSL https://raw.githubusercontent.com/MangiafestoElectronicsLLC/ME_CAM-DEV/main/scripts/auto_setup_mecam.sh | bash
```

What to choose for OS:
- Best default: Raspberry Pi OS Lite (32-bit) Bullseye or Bookworm.
- For Pi Zero 2W: prefer Lite 32-bit for reliability and lower memory pressure.

## Start here

- GitHub-managed Pi install: `docs/GITHUB_INSTALL.md`
- Replit-hosted dashboard flow: `docs/REPLIT_INSTALL.md`
- Security controls and disclosure policy: `SECURITY.md`
- Pi Zero 2W runtime notes: `PI_ZERO_2W_CAMERA_EXPLANATION.md`

---

## 🎯 Key Features

### Multi-Device Management
- **Centralized Dashboard**: Monitor multiple Pi cameras from one interface
- **Device Discovery**: Automatic detection of remote cameras on network
- **Individual Device Pages**: Per-device status, battery, storage, recordings
- **Unified API**: Single endpoint to query all devices
- **Device IP Tracking**: Real-time hostname and IP address monitoring

### Camera & Streaming
- **Fast Streaming**: 15-30 FPS using picamera2 continuous capture
- **Hardware Auto-Detection**: System detects Pi model and optimizes settings
- **TEST MODE**: Graceful fallback for Pi Zero 2W (512MB RAM limit)
- **Fallback Support**: libcamera-still compatibility mode (1-2 FPS)
- **Live Dashboard**: Real-time MJPEG stream in web browser (Pi 3B+/4/5)

### Dashboard & Web Interface
- **Real-Time Updates**: All metrics refresh every 5 seconds automatically
- **Accurate Battery Display**: Shows 0-100% with dynamic status
- **Unified Navbar**: Consistent navigation across all pages
- **Mobile-Friendly**: Responsive design for phones/tablets
- **HTTPS Support**: Self-signed certificates for secure access
- **Domain Access**: Configure custom domain (e.g., https://me_cam.com)

### Motion Detection & Recording
- **Smart Detection**: Motion-triggered recording
- **Background Service**: Non-blocking motion detection
- **Configurable Sensitivity**: Adjust motion threshold (1-100)
- **Event History**: Track all motion events with timestamps
- **Automatic Recording**: Save videos when motion detected

### Storage Management
- **Automatic Cleanup**: Delete old files when storage reaches threshold
- **Date Organization**: Optional YYYY/MM/DD folder structure
- **Retention Policy**: Configurable days to keep recordings
- **Storage Limits**: Set maximum GB usage
- **Real-Time Monitoring**: Dashboard shows storage metrics
- **Manual Controls**: Delete recordings via web interface

### Battery Monitoring
- **Accurate Percentage**: Shows 0-100% based on voltage reading
- **GPIO Support**: Connect battery to GPIO 17 for monitoring
- **Dynamic Updates**: Battery status refreshes every 5 seconds
- **Power State Detection**: Identifies charging vs discharging

### Security & Access
- **User Authentication**: Admin account with password protection
- **HTTPS/SSL**: Self-signed certificates included
- **Domain Support**: Configure custom domain names
- **Session Management**: Secure login sessions
- **API Authentication**: Protected endpoints

---

## 📋 System Requirements

### Hardware
| Component | Minimum | Recommended | Note |
|-----------|---------|-------------|------|
| **Raspberry Pi** | Zero 2W | Pi 3B+ or higher | Pi Zero 2W: No camera display (TEST MODE) |
| **RAM** | 512MB | 1GB+ | Camera display requires 1GB+ RAM |
| **Storage** | 32GB microSD | 64GB+ microSD | Larger = more recordings |
| **Power** | 5V 2A USB-C | 5V 2.5A USB-C | Stable power critical |
| **Network** | WiFi or Ethernet | Ethernet preferred | Stable connection required |

### Software
- **OS**: Raspberry Pi OS Lite (32-bit), Bullseye or Bookworm
- **Python**: 3.9+ (included in Bullseye)
- **Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

---

## 🚀 Quick Installation

### Option 1: Quick Start (Recommended)

See [QUICKSTART.md](QUICKSTART.md) for complete 60-second setup with bash commands.

### Option 2: Manual Installation

#### On Raspberry Pi:

```bash
# 1. Update system and disable legacy camera (CRITICAL!)
sudo apt update && sudo apt upgrade -y
sudo raspi-config
# → Interfacing Options → Camera → NO (disable legacy)
# → Interfacing Options → I2C → YES (enable for battery)
# → Reboot

# 2. Clone repository
cd ~
git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV.git
cd ME_CAM-DEV

# 3. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure
cp config/config_default.json config/config.json
nano config/config.json  # Edit device name, enable features

# 5. Install and start service
sudo cp etc/systemd/system/mecamera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mecamera
sudo systemctl start mecamera
```

### Access Dashboard

Open browser: **http://raspberrypi.local:8080**  
Or: **http://[PI-IP-ADDRESS]:8080**

**Authentication:**  
Create or rotate credentials before exposing the dashboard to any shared network. Avoid relying on example credentials in documentation.

---

## 📖 Documentation

### Quick Reference
- **[docs/GITHUB_INSTALL.md](docs/GITHUB_INSTALL.md)** - Step-by-step GitHub deployment guide
- **[docs/REPLIT_INSTALL.md](docs/REPLIT_INSTALL.md)** - Step-by-step Replit dashboard and enrollment guide
- **[SECURITY.md](SECURITY.md)** - Security controls, disclosure policy, and deployment guidance

### Technical Documentation
- **[PI_ZERO_2W_CAMERA_EXPLANATION.md](PI_ZERO_2W_CAMERA_EXPLANATION.md)** - Pi Zero 2W runtime notes
- **[config/config_default.json](config/config_default.json)** - Configuration options reference
- **Troubleshooting** - See PART 8 in [notes.txt](notes.txt)
- **Multi-Device Setup** - See PART 6 in [notes.txt](notes.txt)

---

## 🔧 Configuration

### Basic Setup (config/config.json)

```json
{
  "device_name": "Front Door Camera",
  "device_id": "camera-001",
  "enable_battery": true,
  "battery_pin": 17,
  "enable_camera": true,
  "camera_fps": "auto",
  "enable_motion": true,
  "motion_threshold": 15,
  "remote_devices": []
}
```

### Multi-Device Setup

Add remote cameras to primary Pi's config:

```json
{
  "remote_devices": [
    {
      "device_id": "camera-garage",
      "name": "Garage Camera",
      "hostname": "camera-garage.local",
      "ip_address": "192.168.1.50",
      "port": 8080,
      "enabled": true
    }
  ]
}
```

Access all devices from "📡 Devices" page in dashboard.

---

## 🌐 API Endpoints

### Device Status
```bash
GET /api/status              # Primary device status
GET /api/battery             # Battery percentage (0-100%)
GET /api/storage             # Disk usage metrics
GET /api/recordings          # List of recorded videos
GET /api/motion/events       # Motion detection events
```

### Multi-Device (NEW)
```bash
GET /api/devices                           # List all devices
GET /api/devices/<device_id>/status        # Remote device status
GET /api/devices/<device_id>/battery       # Remote device battery
GET /api/devices/<device_id>/storage       # Remote device storage
```

**Release note summary**: see the V3 workflow-generated GitHub release notes for the tagged version you ship.

---

## 🗂️ Project Structure

```
ME_CAM-DEV/
├── main.py                      # Application entry point
├── hub.py                       # Multi-device hub
├── requirements.txt             # Python dependencies
├── notes.txt                    # Legacy setup guide
├── README.md                    # This file
│
├── src/                         # Source code
│   ├── core/                    # Core functionality
│   │   ├── config_manager.py
│   │   ├── user_auth.py
│   │   ├── battery_monitor.py
│   │   └── ...
│   ├── camera/                  # Camera modules
│   │   ├── camera_coordinator.py
│   │   ├── fast_camera_streamer.py
│   │   └── ...
│   ├── detection/               # Motion detection
│   │   ├── motion_service.py
│   │   └── ...
│   └── utils/                   # Utilities
│       └── pi_detect.py         # Pi model auto-detection
│
├── web/                         # Web dashboard
│   ├── app.py                   # Flask application
│   ├── templates/               # HTML templates
│   │   ├── user_dashboard.html  # Main dashboard
│   │   ├── devices.html         # Multi-device page
│   │   └── ...
│   └── static/                  # CSS, JS, images
│
├── config/                      # Configuration
│   ├── config.json              # User settings (YOU EDIT THIS)
│   └── config_default.json      # Template reference
│
├── certs/                       # SSL certificates
│   ├── certificate.pem
│   └── private_key.pem
│
├── etc/systemd/system/
│   └── mecamera.service         # SystemD service file
│
├── scripts/                     # Maintenance scripts
│   ├── setup.sh
│   ├── deploy_pi_zero.sh
│   └── ...
│
├── docs/                        # Documentation
│   ├── PROJECT_GUIDE.md
│   └── ...
│
├── logs/                        # Application logs
├── recordings/                  # Video storage
└── tests/                       # Unit tests
```

---

## 🏆 Performance by Pi Model

| Pi Model | RAM | Camera FPS | Display? | Best Use |
|----------|-----|------------|----------|----------|
| **Zero 2W** | 512MB | TEST MODE | ❌ No | Recording, motion detection |
| **3B+** | 1GB | 15 FPS | ✅ Yes | Full HD streaming |
| **4** | 2-8GB | 30 FPS | ✅ Yes | Multi-device hub |
| **5** | 4-8GB | 30+ FPS | ✅ Yes | 4K capable |

**Why Pi Zero 2W?** 512MB RAM < 250MB camera buffer needed = TEST MODE (correct behavior)

---

## 🔧 Common Commands

### Service Management
```bash
sudo systemctl start mecamera      # Start service
sudo systemctl stop mecamera       # Stop service
sudo systemctl restart mecamera    # Restart service
sudo systemctl status mecamera     # Check status
sudo journalctl -u mecamera -f     # View logs
```

### System Info
```bash
hostname -I                        # Get IP address
df -h                              # Check disk space
free -m                            # Check memory
sudo vcgencmd get_camera           # Check camera detection
```

### Testing
```bash
curl http://127.0.0.1:8080/api/status          # Test API
curl http://127.0.0.1:8080/api/battery         # Check battery
curl http://127.0.0.1:8080/api/devices         # List devices
```

---

## 🐛 Troubleshooting

### Dashboard is Slow (1-2 FPS)

**Solution:** Install picamera2 for 15x speed boost

```bash
cd ~/ME_CAM-DEV
sudo ./scripts/install_fast_camera.sh
```

Then enable in Settings → Performance → ✓ Use Fast Streaming

### Camera Not Detected

```bash
# Test camera
libcamera-still --list-cameras

# If shows "No cameras available", check boot config:
grep camera_auto_detect /boot/config.txt

# Should show: camera_auto_detect=1
# If it shows =0, fix it:
sudo sed -i 's/camera_auto_detect=0/camera_auto_detect=1/g' /boot/config.txt
sudo reboot
```

### Motion Detection Not Working

```bash
# Check service status
sudo systemctl status mecamera | grep MOTION

# Check logs
tail -f logs/mecam.log | grep MOTION

# Verify enabled in config
grep "motion_only" config/config.json
# Should show: "motion_only": true

# Test by waving hand in front of camera
# Recording should appear in: ls -lh recordings/
```

### Storage Full

```bash
# Check usage
df -h

# Manual cleanup via API
curl http://localhost:8080/api/storage/cleanup -X POST

# Or use dashboard: Settings → Clear All Recordings
```

### Emergency Alerts Not Sending

1. **Check email configured**: Settings → Email Notifications
2. **Use Gmail App Password** (not regular password)
   - Get from: https://myaccount.google.com/apppasswords
3. **Check carrier gateway correct**
   - Wrong gateway = no SMS received
4. **Check first message not in spam**
5. **Test**: Dashboard → 🚨 SOS Alert button

---

## 📚 Documentation

---

## 🐛 Troubleshooting

### Common Issues

**❌ "Camera Hardware Detection Failed" on Pi Zero 2W**  
✅ **This is correct!** Pi Zero 2W has only 512MB RAM (camera needs 250MB+)  
📖 Read: [PI_ZERO_2W_CAMERA_EXPLANATION.md](PI_ZERO_2W_CAMERA_EXPLANATION.md)  
💡 Solution: Use Pi 3B+ or higher, or use Zero 2W for recording only

**❌ Dashboard shows "OFFLINE" but Pi responds to SSH**  
```bash
sudo systemctl restart mecamera
sudo journalctl -u mecamera -n 50
```

**❌ Battery shows 0% or wrong percentage**  
Check GPIO 17 connection, unplug/replug power to reset

**❌ Can't access https://me_cam.com**  
Edit hosts file, add: `[PI-IP] me_cam.com`, flush DNS cache

**📖 Full Troubleshooting**: See PART 8 in [notes.txt](notes.txt)

---

## 💻 Software Requirements

- **OS**: Raspberry Pi OS Bullseye (32-bit) - **Bookworm NOT supported**
- **Python**: 3.9+ (included in Bullseye)
- **picamera2**: Camera support (auto-installed)
- **Flask**: 2.2.5 (web framework)

---

## 🤝 Contributing

This is the **development branch** - main branch coming soon.

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Test on actual Pi hardware
4. Update documentation
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **📖 Docs**: [QUICKSTART.md](QUICKSTART.md) or [notes.txt](notes.txt)
- **❓ Issues**: https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV/issues
- **💬 Discussions**: https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV/discussions

---

## ✅ Project Status

### Completed
- ✅ Fast streaming (15-30 FPS)
- ✅ Multi-device support
- ✅ Battery monitoring (accurate %)
- ✅ Storage management
- ✅ Web dashboard (5-sec refresh)
- ✅ HTTPS support
- ✅ Pi model auto-detection
- ✅ Complete documentation (70+ KB)

### In Development
- 🚧 Recording scheduling
- 🚧 Advanced motion settings
- 🚧 Mobile app support

### Planned
- 📋 Cloud storage improvements
- 📋 WebRTC streaming
- 📋 Object detection
- 📋 Hardware acceleration

---

## 📝 Changelog

### Legacy V2 notes
#### Fixed
- 🐛 Battery display (accurate 0-100%)
- 🐛 Dashboard auto-refresh (5-sec updates)
- 🐛 Navbar consistency (Devices link)
- 🐛 Multi-device API responses

#### New Features
- ✨ **LITE MODE** for Pi Zero 2W (~150MB RAM instead of ~400MB)
- ✨ Pi model auto-detection
- ✨ Device IP tracking
- ✨ API documentation
- ✨ Auto-mode switching (LITE for Zero 2W, Standard for others)

#### Documentation
- 📚 Rewrote [notes.txt](notes.txt) (24KB, LITE MODE guide added)
- 📚 Created [PI_ZERO_2W_CAMERA_EXPLANATION.md](PI_ZERO_2W_CAMERA_EXPLANATION.md)
- 📚 Created [QUICKSTART.md](QUICKSTART.md)
- Updated release documentation is now generated from the V3 workflow and release tag
- 📚 Updated .gitignore (production-ready)

### v2.0.0 (January 13, 2026)
- ✨ Fast streaming mode (15-30 FPS)
- ✨ Organized src/ structure
- ✨ Advanced storage management
- 🐛 Camera conflicts fixed
- ⚡ 60% less CPU usage

### v1.x (2025)
- Initial release

---

**Version**: 3.0.0  
**Release posture**: documentation, tests, and release hygiene refreshed for public delivery  
**Maintained by**: MangiafestoElectronics LLC

---

**ME_CAM v3.0.0 - Raspberry Pi focused, security-hardened, and release-gated**
