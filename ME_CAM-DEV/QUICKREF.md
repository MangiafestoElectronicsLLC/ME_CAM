# ME_CAM Quick Reference

## 🚀 Quick Deploy (5 Steps)

### Step 1: Copy Code to Pi
```powershell
# Windows PowerShell:
scp -r "C:\Users\nickp\Downloads\ME_CAM-DEV\ME_CAM-DEV\*" pi@<pi-ip>:~/ME_CAM/
```

### Step 2: Setup Thumbnails Directory
```bash
# SSH to Pi:
mkdir -p ~/ME_CAM/web/static/thumbs
```

### Step 3: Restart Service
```bash
sudo systemctl restart mecamera.service
```

### Step 4: Verify
```bash
# Check logs:
sudo journalctl -u mecamera.service -n 10

# Should see no errors
```

### Step 5: Access Dashboard
```
http://<pi-ip>:8080
PIN: 1234
```

---

## 📍 Key URLs

| Feature | URL |
|---------|-----|
| Dashboard | http://\<ip\>:8080 |
| Login | http://\<ip\>:8080/login |
| Settings | http://\<ip\>:8080/config |
| Live Stream | http://\<ip\>:8080/api/stream |
| Status API | http://\<ip\>:8080/api/status |

---

## 🎨 Dashboard Highlights

✅ **5 Status Cards**
- System (device name + online/offline)
- Battery (% or "External Power")
- Storage (GB used + bar)
- Recordings (total count)
- History (24h events)

✅ **Live Feed**
- MJPEG stream (640x480 @ 30fps)
- Real-time video

✅ **Recordings Grid**
- Thumbnail previews ← **NEW**
- Video name + date
- Clickable for future features

✅ **Emergency Button**
- Large red SOS
- Confirms before alert
- Logs emergency contact

---

## ⚙️ Settings Page (/config)

### System Integration
- [ ] WiFi Configuration (toggle)
- [ ] Bluetooth Support (toggle)

### Email Alerts
- [ ] Enable Email Alerts (toggle)
  - SMTP Server: `smtp.gmail.com` (Gmail)
  - SMTP Port: `587`
  - Username: `your-email@gmail.com`
  - Password: `app-password` (not regular password)
  - From: `alerts@safehome.local`
  - To: `recipient@example.com`

### Google Drive
- [ ] Enable Google Drive (toggle)
  - Folder ID: Get from drive.google.com folder URL

---

## 🔐 Default Credentials

| Item | Value |
|------|-------|
| Dashboard PIN | `1234` |
| Encryption | Enabled (auto) |
| Storage Key | `config/storage_key.key` (auto-generated) |

**⚠️ Always change PIN after first-run setup!**

---

## 📁 File Locations on Pi

```
/home/pi/ME_CAM/
├── recordings/                    # Plaintext videos
├── recordings_encrypted/          # Encrypted videos
├── web/static/thumbs/             # Video thumbnails ← NEW
├── logs/                          # System logs
├── config/
│   ├── config.json               # Active configuration
│   └── storage_key.key           # Encryption key
└── ...code files...
```

---

## 🛠️ Common Commands

### Monitor Logs (Real-Time)
```bash
sudo journalctl -u mecamera.service -f
# Press Ctrl+C to exit
```

### Change PIN
```bash
nano ~/ME_CAM/config/config.json
# Edit: "pin_code": "1234" → your new PIN
sudo systemctl restart mecamera.service
```

### View Recordings
```bash
ls -lh ~/ME_CAM/recordings/                # Plaintext
ls -lh ~/ME_CAM/recordings_encrypted/      # Encrypted
```

### Stop Service
```bash
sudo systemctl stop mecamera.service
```

### Start Service
```bash
sudo systemctl start mecamera.service
```

### Restart Service
```bash
sudo systemctl restart mecamera.service
```

### Check Service Status
```bash
sudo systemctl status mecamera.service
```

---

## 🐛 Troubleshooting

### Dashboard Won't Load
1. Check service: `sudo systemctl status mecamera.service`
2. Check camera: `libcamera-hello --list-cameras`
3. Restart service: `sudo systemctl restart mecamera.service`
4. View logs: `sudo journalctl -u mecamera.service -f`

### No Thumbnails
1. Check directory: `ls ~/ME_CAM/web/static/thumbs/`
2. Test OpenCV: `python3 -c "import cv2; print(cv2.__version__)"`
3. Make directory writable: `chmod 755 ~/ME_CAM/web/static/thumbs/`

### Login Loop
1. Clear browser cookies (Ctrl+Shift+Delete)
2. Check PIN in config: `grep pin_code ~/ME_CAM/config/config.json`
3. Try default: `1234`

### No Recordings
1. Check motion detection: Move hand in front of camera
2. Check settings: Verify detection enabled and sensitivity tuned
3. Check storage: `ls -la ~/ME_CAM/recordings/`
4. Check permissions: `ls -ld ~/ME_CAM/recordings/`

---

## 📊 What's New This Release

### Features Added
✅ **Thumbnail Generation**
- First-frame extraction from videos
- Automatic display in recordings grid
- thumbnail_gen.py utility

✅ **Live Stream**
- MJPEG endpoint at /api/stream
- 640x480 @ 30fps
- Auth-gated access

✅ **Settings Page**
- In-app configuration UI (/config)
- Email notifications setup
- Google Drive backup setup
- WiFi & Bluetooth toggles
- Persistent to config.json

✅ **Optional Integrations**
- Email alerts (SMTP)
- Google Drive backup (Folder ID)
- WiFi configuration
- Bluetooth support
- All configurable via Settings page

---

## 📖 Documentation Files

1. **DEPLOYMENT.md** (150+ lines)
   - Complete deployment guide
   - Fresh Pi setup
   - Systemd service configuration
   - Troubleshooting guide

2. **FEATURE_CHECKLIST.md** (350+ lines)
   - Feature completion status
   - Implementation details
   - QA test cases
   - Verification checklist

3. **README_FINAL.md**
   - Project overview
   - API documentation
   - Configuration schema
   - Common tasks

4. **IMPLEMENTATION_SUMMARY.md**
   - Technical details
   - Code modifications
   - Deployment instructions

5. **QUICKREF.md** (This File)
   - Quick commands
   - Key URLs
   - Common tasks
   - Troubleshooting

---

## 🎯 Next Steps

1. **Deploy**: Copy code to Pi via SCP
2. **Setup**: `mkdir -p ~/ME_CAM/web/static/thumbs`
3. **Restart**: `sudo systemctl restart mecamera.service`
4. **Access**: http://\<ip\>:8080
5. **Configure**: Go to ⚙️ Settings
6. **Monitor**: `sudo journalctl -u mecamera.service -f`

---

## 📞 Support

**Check Logs**:
```bash
sudo journalctl -u mecamera.service -f
```

**See Full Docs**:
- DEPLOYMENT.md - Setup & troubleshooting
- FEATURE_CHECKLIST.md - What's implemented
- README_FINAL.md - API & configuration

---

**Version**: 1.0 Final  
**Status**: Production Ready ✅  
**Tested On**: Raspberry Pi Zero 2 W  
