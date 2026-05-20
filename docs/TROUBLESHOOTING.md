# ME_CAM Troubleshooting Guide

Common issues and solutions for ME_CAM deployments.

## Quick Diagnostics

### Check Service Status
```bash
sudo systemctl status mecamera
```

### View Recent Logs
```bash
# Last 50 lines
tail -50 logs/app.log

# Real-time monitoring
tail -f logs/app.log

# Search for errors
grep ERROR logs/app.log | tail -20
```

### Test API Connectivity
```bash
# Health check (no auth required)
curl -k https://camera.local:8443/api/health

# Device status (requires token)
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://camera.local:8443/api/status
```

### Check Device Resources
```bash
# Memory usage
free -h

# Disk space
df -h

# CPU temperature
vcgencmd measure_temp

# Running processes
ps aux | grep -E "python|camera"
```

---

## Common Issues

### Issue: "Camera not found" or "libcamera-still not available"

**Symptoms**: Service fails to start, logs show camera initialization errors

**Diagnosis**:
```bash
# Check if libcamera is installed
libcamera-hello --list-cameras

# Verify camera is enabled in raspi-config
sudo raspi-config nonint get_camera

# Check dmesg for hardware errors
dmesg | grep -i camera
```

**Solutions**:

1. **Enable camera in raspi-config**
   ```bash
   sudo raspi-config
   # Navigate to Interface Options → Camera → Enable
   ```

2. **Update Pi OS packages**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y libcamera-tools
   ```

3. **Check camera ribbon cable**
   - Power off Pi
   - Reseat camera ribbon cable (blue tab pulls toward HDMI port)
   - Power on and test

4. **Try test capture**
   ```bash
   libcamera-still -o test.jpg
   ```

5. **Use fallback camera module**
   ```bash
   # In config.json
   "camera": {"model": "auto"}  # Force auto-detection
   ```

---

### Issue: "Authentication failed" or "Invalid token"

**Symptoms**: API requests return 401 Unauthorized

**Diagnosis**:
```bash
# Check enrollment key file
cat /opt/me_cam/enrollment_key.txt

# Verify token format
echo "Authorization: Bearer $TOKEN"
```

**Solutions**:

1. **Regenerate enrollment key**
   ```bash
   python -c "
   from src.core.user_auth import generate_enrollment_key
   key = generate_enrollment_key()
   with open('/opt/me_cam/enrollment_key.txt', 'w') as f:
       f.write(key)
   print(f'New key: {key}')
   "
   sudo systemctl restart mecamera
   ```

2. **Check token expiration**
   - Keys typically expire after 1 year
   - Check logs for expiration messages
   - Generate new key and update client

3. **Verify API call format**
   ```bash
   # Correct format
   curl -H "Authorization: Bearer token_here" https://camera.local:8443/api/status
   
   # Wrong formats (don't use)
   curl -H "Bearer: token_here" ...
   curl -H "Auth: token_here" ...
   ```

---

### Issue: "HTTPS certificate error" or "connection refused"

**Symptoms**: Browser shows SSL/TLS warnings, `curl: (60) SSL certificate problem`

**Solutions**:

1. **For testing, ignore certificate warning**
   ```bash
   curl -k https://camera.local:8443/api/health
   # -k flag ignores certificate verification
   ```

2. **Add certificate to system trust store**
   ```bash
   # Linux
   sudo cp certs/server.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   
   # macOS
   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/server.crt
   ```

3. **Generate new self-signed certificate**
   ```bash
   openssl req -x509 -newkey rsa:2048 -nodes \
     -keyout certs/server.key \
     -out certs/server.crt \
     -days 365 \
     -subj "/CN=camera.local"
   sudo systemctl restart mecamera
   ```

4. **Use custom domain certificate**
   ```bash
   # Obtain certificate (Let's Encrypt)
   # Copy to device
   scp fullchain.pem pi@camera.local:/opt/me_cam/certs/server.crt
   scp privkey.pem pi@camera.local:/opt/me_cam/certs/server.key
   ssh pi@camera.local 'sudo systemctl restart mecamera'
   ```

---

### Issue: "Motion detection not working" or "No motion events recorded"

**Symptoms**: Motion events not appearing in logs, recordings not triggered

**Diagnosis**:
```bash
# Check motion detection is enabled
grep -i "motion_detection" logs/app.log

# Check sensitivity setting
python -c "from src.core.config_manager import load_config; c = load_config(); print(c.get('recording', {}).get('motion_sensitivity', 50))"

# Monitor motion frames
tail -f logs/app.log | grep -i motion
```

**Solutions**:

1. **Lower sensitivity threshold**
   ```bash
   # In config.json, reduce sensitivity (1-100, lower = more sensitive)
   "recording": {
     "motion_sensitivity": 40  # Was 50
   }
   sudo systemctl restart mecamera
   ```

2. **Test with visible motion**
   ```bash
   # Move hand/object in front of camera
   tail -f logs/app.log | grep -i "motion\|detection"
   ```

3. **Increase minimum duration**
   ```bash
   # Ignore fleeting motion (noise)
   "recording": {
     "motion_min_duration_ms": 1000  # 1 second minimum
   }
   ```

4. **Check camera frames are capturing**
   ```bash
   # Get snapshot
   curl -k -H "Authorization: Bearer $TOKEN" \
     https://camera.local:8443/api/snapshot -o snapshot.jpg
   file snapshot.jpg  # Verify JPEG size > 0
   ```

---

### Issue: "Disk full" or "Storage cleanup not working"

**Symptoms**: Storage fills up, cleanup not running, recordings stop

**Diagnosis**:
```bash
df -h  # Check disk usage
ls -lh recordings/  # Check recording size
grep -i "cleanup\|storage" logs/app.log
```

**Solutions**:

1. **Manual cleanup**
   ```bash
   # Find and delete old recordings
   find recordings/ -type f -mtime +30 -delete
   
   # Delete by size (largest first)
   ls -lhS recordings/ | head -20
   ```

2. **Enable automatic cleanup**
   ```bash
   # In config.json
   "recording": {
     "cleanup_enabled": true,
     "cleanup_threshold_percent": 80,
     "retention_days": 30
   }
   sudo systemctl restart mecamera
   ```

3. **Lower retention policy**
   ```bash
   # Keep only 7 days instead of 30
   "recording": {
     "retention_days": 7
   }
   ```

4. **Set hard limit**
   ```bash
   # Stop storing new files at 50GB
   "recording": {
     "retention_gb_max": 50
   }
   ```

---

### Issue: "High CPU usage" or "Camera freezing"

**Symptoms**: Process consuming 80%+ CPU, stream stuttering, device slow

**Diagnosis**:
```bash
# Check CPU usage
top -b -n 1 | grep python

# Check camera framerate
grep "fps\|framerate" logs/app.log

# Monitor thermal throttling
vcgencmd measure_clock arm  # Should be stable
```

**Solutions**:

1. **Lower framerate**
   ```bash
   # In config.json
   "camera": {
     "framerate": 10  # Was 30
   }
   sudo systemctl restart mecamera
   ```

2. **Lower resolution**
   ```bash
   "camera": {
     "resolution": "1280x720"  # Was 1920x1440
   }
   ```

3. **Disable motion detection**
   ```bash
   "recording": {
     "motion_detection": false
   }
   ```

4. **Switch to lite mode (Pi Zero 2W)**
   ```bash
   # Use main_lite.py instead of main.py
   sudo sed -i 's/main\.py/main_lite.py/' /etc/systemd/system/mecamera.service
   sudo systemctl daemon-reload
   sudo systemctl restart mecamera
   ```

5. **Check for memory leaks**
   ```bash
   # Monitor memory over time
   watch -n 5 'free -h; ps aux | grep python'
   
   # If growing unbounded, restart service
   sudo systemctl restart mecamera
   ```

---

### Issue: "Stream connection lost" or "MJPEG drops"

**Symptoms**: Video stream freezes, frequent disconnections from browser

**Diagnosis**:
```bash
# Test stream with timeout
timeout 30 curl -k -H "Authorization: Bearer $TOKEN" \
  https://camera.local:8443/api/stream -o stream.mjpeg
# Should produce multi-MB file in 30 seconds

# Check network quality
ping -c 10 camera.local  # Look for packet loss
```

**Solutions**:

1. **Reduce stream quality**
   ```bash
   # ?quality=low in API requests
   curl https://camera.local:8443/api/stream?quality=low -o stream.mjpeg
   ```

2. **Lower framerate**
   ```bash
   # ?framerate=10 in API requests  
   curl https://camera.local:8443/api/stream?framerate=10 -o stream.mjpeg
   ```

3. **Check network bandwidth**
   ```bash
   # Test local network speed
   iperf3 -c [other_device]
   
   # Check Pi's WiFi signal
   iwconfig  # Look for signal strength
   ```

4. **Move closer to WiFi router** (if using WiFi)

5. **Use Ethernet** for more reliable connection

---

### Issue: "Rate limited" (429 Too Many Requests)

**Symptoms**: Getting HTTP 429 errors from API

**Diagnosis**:
```bash
grep "429\|rate" logs/app.log

# Check request frequency
curl -v -H "Authorization: Bearer $TOKEN" \
  https://camera.local:8443/api/status 2>&1 | grep "X-RateLimit"
```

**Solutions**:

1. **Reduce request frequency**
   - Dashboard refreshes every 5 seconds by default
   - Set refresh to 10+ seconds

2. **Increase rate limits (config.json)**
   ```bash
   "security": {
     "general_rate_limit_per_minute": 200  # Was 100
   }
   ```

3. **Wait for rate limit reset**
   - Check `Retry-After` header
   - Typically resets each minute

---

### Issue: "CSRF token validation failed"

**Symptoms**: State-changing requests (POST/PUT) return 403 Forbidden

**Diagnosis**:
```bash
# Test GET (should always work)
curl https://camera.local:8443/api/status

# Test POST without CSRF (will fail)
curl -X POST https://camera.local:8443/api/recording/start
```

**Solutions**:

1. **Get CSRF token first**
   ```bash
   # Token in response headers or cookies
   curl -k -c cookies.txt https://camera.local:8443/dashboard
   ```

2. **Send CSRF token in request**
   ```bash
   curl -X POST \
     -b cookies.txt \
     -H "X-CSRF-Token: $TOKEN" \
     https://camera.local:8443/api/recording/start
   ```

3. **Disable CSRF (dev only, never production)**
   ```bash
   "security": {
     "csrf_protection_enabled": false
   }
   ```

---

## Performance Tuning

### For Pi Zero 2W (512MB RAM)

```bash
# Use lite mode
python main_lite.py

# Lower camera settings
# config.json:
# - resolution: 1280x720
# - framerate: 10
# - quality: low

# Disable optional features
# - motion_detection: false
# - person_detection_enabled: false
```

### For Pi 4B (2GB+ RAM)

```bash
# Standard mode is fine
python main.py

# Can handle higher settings
# - resolution: 1920x1440
# - framerate: 30
# - motion_detection: true
```

---

## Log Analysis

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python main.py
```

### Find Errors
```bash
grep -i error logs/app.log
grep -i warning logs/app.log
grep -i exception logs/app.log
```

### Analyze Startup Sequence
```bash
head -100 logs/app.log
```

### Check for Memory Issues
```bash
grep -i "memory\|failed.*alloc" logs/app.log
```

---

## Getting Help

### Gather Diagnostic Information

```bash
#!/bin/bash
echo "=== System Info ==="
uname -a
vcgencmd measure_temp

echo "=== ME_CAM Status ==="
sudo systemctl status mecamera

echo "=== Recent Logs ==="
tail -100 logs/app.log

echo "=== Disk Usage ==="
df -h

echo "=== Memory ==="
free -h

echo "=== Camera Test ==="
libcamera-hello --list-cameras

echo "=== API Test ==="
curl -k https://camera.local:8443/api/health
```

Then report issue at: https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV/issues

---

## Emergency Recovery

### Restart Service
```bash
sudo systemctl restart mecamera
```

### Reset to Defaults
```bash
cp config/config_default.json config/config.json
```

### Reinstall from Scratch
```bash
cd /home/pi
rm -rf ME_CAM-DEV
git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV.git
cd ME_CAM-DEV
bash scripts/auto_setup_mecam.sh
```

### Factory Reset (last resort)
```bash
# Backs up current config
sudo mkdir -p /opt/me_cam/backups
sudo cp -r /opt/me_cam/config /opt/me_cam/backups/config.backup

# Remove all ME_CAM files
sudo rm -rf /opt/me_cam
sudo rm -rf ~/.ME_CAM

# Reflash microSD card
# Use Raspberry Pi Imager to write fresh Raspberry Pi OS Lite image
```

---

**Still stuck?** Check [GitHub Discussions](https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV/discussions) or file an issue with diagnostic information.
