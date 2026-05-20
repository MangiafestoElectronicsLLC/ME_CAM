# ME_CAM Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    END USER / DASHBOARD                      │
│  (Web Browser - Chrome, Firefox, Safari on any device)      │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS (Optional VPN)
┌────────────────────▼────────────────────────────────────────┐
│              FLASK WEB APPLICATION LAYER                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Routes & Controllers (web/app.py)                  │  │
│  │  - /api/status, /api/stream, /api/recordings        │  │
│  │  - /dashboard, /auth/login, /config                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│          SECURITY MIDDLEWARE LAYER (CRITICAL)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • CSRF Token Validation (per request)               │  │
│  │  • Authentication & Authorization                    │  │
│  │  • Rate Limiting (general + login-specific)          │  │
│  │  • Request/Response Sanitization                     │  │
│  │  • Security Headers (CSP, X-Frame-Options, etc)      │  │
│  │  • Audit Logging                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│           BUSINESS LOGIC / CORE SERVICES                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Camera Pipeline (src/camera/)                       │  │
│  │  • rpicam_streamer.py (picamera2/libcamera)          │  │
│  │  • Frame capture & encoding (H.264 optimized)        │  │
│  │  • Resolution/FPS adaptation                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Motion Detection (src/motion/)                      │  │
│  │  • Background subtraction algorithm                  │  │
│  │  • Sensitivity-based filtering                       │  │
│  │  • Event queuing & notification                      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Recording Management (src/recording/)               │  │
│  │  • On-demand & motion-triggered recording            │  │
│  │  • H.264 codec, adaptive bitrate                     │  │
│  │  • Queue management for async writes                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│        HARDWARE ABSTRACTION LAYER (HAL)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Device Detection (hardware_detect.py)               │  │
│  │  • Pi model identification (Zero 2W, 4B, 5)          │  │
│  │  • Camera module detection (v2, IMX519, etc)         │  │
│  │  • RAM/Storage inventory                             │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Power Management (power_manager.py)                 │  │
│  │  • Battery monitoring (voltage, current)             │  │
│  │  • Thermal management                                │  │
│  │  • CPU/GPU frequency scaling                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  Storage Management (storage_manager.py)             │  │
│  │  • Partition monitoring                              │  │
│  │  • Cleanup when threshold reached                    │  │
│  │  • Log rotation & archival                           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  System Utilities                                    │  │
│  │  • WiFi configuration (nmcli wrapper)                │  │
│  │  • systemd service management                        │  │
│  │  • Clock synchronization                             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│          OPERATING SYSTEM & HARDWARE                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Raspberry Pi OS Lite (Bullseye/Bookworm)            │  │
│  │  • Linux Kernel                                      │  │
│  │  • libcamera/picamera2                               │  │
│  │  • FFmpeg/libavformat                                │  │
│  │  • ALSA (audio, optional)                            │  │
│  │                                                       │  │
│  │  Raspberry Pi Hardware                               │  │
│  │  • BCM2835/2711/2712 SoC                             │  │
│  │  • GPU (VideoCore IV/VI)                             │  │
│  │  • Camera interface (CSI)                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Web Application Layer (Flask)

**File**: `web/app.py` | `main_lite.py`

Responsibilities:
- HTTP/HTTPS request handling
- REST API endpoint implementation
- Static file serving (dashboard HTML/CSS/JS)
- Session management
- Template rendering

**Key Routes**:
- `GET /api/status` - Device metrics
- `GET /api/stream` - Live MJPEG stream
- `GET /api/snapshot` - Single frame capture
- `POST /api/recording/start` - Manual recording
- `GET /api/events` - Motion event history

---

### 2. Security Middleware

**File**: `src/core/security_middleware.py` | `src/core/security.py`

Responsibilities:
- CSRF token generation and validation
- Authentication via enrollment keys
- Rate limiting (token bucket algorithm)
- Request sanitization
- Security header injection
- Audit logging of sensitive operations

**Protected Resources**:
- All `/api/*` endpoints (except `/api/health`)
- `/dashboard` and admin endpoints
- `/config` modification endpoints

---

### 3. Camera Pipeline

**File**: `src/camera/rpicam_streamer.py`

Responsibilities:
- Initialize camera (libcamera/picamera2)
- Continuous frame capture loop
- H.264 encoding (hardware-accelerated)
- MJPEG stream generation
- Frame timestamping
- Motion detection frame queue

**Performance Tuning**:
- Pi 4B/5: 28 FPS @ 1920x1440
- Pi Zero 2W (Lite): 8 FPS @ 1280x720 (limited by 512MB RAM)

---

### 4. Motion Detection

**File**: `src/motion/motion_detector.py`

Responsibilities:
- Background subtraction (frame differencing)
- Morphological operations (erosion/dilation)
- Contour detection
- Sensitivity threshold comparison
- Event notification queueing

**Algorithm**:
```
1. Capture frame from camera
2. Convert BGR → Grayscale
3. Apply Gaussian blur (reduce noise)
4. Compare with background image
5. Apply morphological ops (clean artifacts)
6. Count pixels above sensitivity threshold
7. If threshold exceeded → motion event
8. Queue event for notification/recording
```

---

### 5. Recording Management

**File**: `src/recording/recorder.py`

Responsibilities:
- Queue recordings (motion-triggered or manual)
- Encode frames to H.264 video
- Write MP4 containers with metadata
- Manage concurrent recordings
- Clean up old files based on retention policy

**Recording Queue**:
```
Motion Detector → Event Queue → Recorder Service → MP4 File
                                (async worker)
```

---

### 6. Hardware Abstraction

**File**: `src/core/hardware_detect.py` | `src/core/power_manager.py`

Responsibilities:
- Detect Pi model at startup
- Select appropriate camera module driver
- Monitor thermal and power metrics
- Trigger frequency scaling if needed
- Battery estimation algorithms

**Device Detection**:
- `/proc/device-tree/model` - Model string
- `/proc/cpuinfo` - Serial number, revision
- GPIO testing - Camera presence detection

---

## Data Flow Examples

### Example 1: Live Stream Request

```
User Browser (HTTPS GET /api/stream)
    ↓
Flask Route Handler (/api/stream)
    ↓
Security Middleware (validate token, rate limit)
    ↓
Camera Pipeline (capture frames continuously)
    ↓
MJPEG Encoder (convert to MJPEG boundary format)
    ↓
HTTP Response (multipart/x-mixed-replace)
    ↓
Browser renders MJPEG stream
```

### Example 2: Motion-Triggered Recording

```
Camera captures frame continuously
    ↓
Motion Detector (background subtraction)
    ↓
Sensitivity threshold exceeded?
    ↓ YES
Event Queue (timestamp, confidence)
    ↓
Recording Service (async worker)
    ↓
Encoder (H.264 MP4 file)
    ↓
Storage Manager (check retention)
    ↓
File saved to disk
    ↓
Notification Service (email/webhook optional)
```

### Example 3: API Request with Authentication

```
Client Request (Bearer token in Authorization header)
    ↓
Flask receives request
    ↓
Security Middleware extracts token
    ↓
Validate token against enrollment keys
    ↓ INVALID
Return 401 Unauthorized
    ↓ VALID
Rate limiting check
    ↓ EXCEEDED
Return 429 Too Many Requests
    ↓ OK
CSRF token validation (if state-changing)
    ↓ FAILED
Return 403 Forbidden
    ↓ PASSED
Route handler executes
    ↓
Response sent with security headers
```

---

## Performance Characteristics

### Memory Usage

| Component | Lite Mode | Standard Mode |
|-----------|-----------|---------------|
| Flask app | 25 MB | 30 MB |
| Camera pipeline | 45 MB | 120 MB (buffering) |
| Motion detection | 15 MB | 15 MB |
| Recording queue | 20 MB | 50 MB |
| System overhead | ~80 MB | ~100 MB |
| **Total** | **~185 MB** | **~315 MB** |

Pi Zero 2W (512 MB): Fits in lite mode with 327 MB available
Pi 4B (2 GB): Comfortable in standard mode

### CPU Usage

| Operation | Lite Mode | Standard Mode |
|-----------|-----------|---------------|
| Streaming only | 8% | 12% |
| + Motion detect | 35% | 25% |
| + Recording | 45% | 40% |

Both modes benefit from hardware video encoder (saves 30% CPU).

---

## Configuration & Deployment Modes

### Fresh Install Path

```
1. Flash Raspberry Pi OS Lite
2. Run auto_setup_mecam.sh OR manual installation
3. Device auto-detects config requirements
4. Enrollment key generated
5. Service enabled and started
6. Accessible at https://hostname.local:8443
```

### Lite Mode Path (Pi Zero 2W)

```
1. Flash Pi OS Lite
2. Run scripts/install_lite_mode.sh
3. main_lite.py used instead of main.py
4. Reduced frame buffering
5. Disabled optional ML modules
6. Still provides full security/API
```

### Hosted Dashboard (Replit)

```
1. Device(s) connect to hub dashboard
2. Dashboard aggregates multiple devices
3. Centralized authentication
4. Cloud-optional recording storage
5. Mobile-friendly interface
```

---

## Security Layers (Defense in Depth)

```
┌─ Layer 1: Network Security
│  ├─ HTTPS/TLS (self-signed or custom)
│  ├─ Optional VPN (Tailscale, WireGuard)
│  └─ Rate limiting on all endpoints
│
├─ Layer 2: Application Security
│  ├─ CSRF token validation
│  ├─ Authentication (enrollment keys)
│  ├─ Input validation & sanitization
│  └─ Secure headers
│
├─ Layer 3: Data Security
│  ├─ Password hashing (PBKDF2)
│  ├─ Enrollment key rotation
│  ├─ Sensitive data excluded from logs
│  └─ Secure temporary file cleanup
│
└─ Layer 4: System Security
   ├─ systemd service isolation
   ├─ File permissions (600 config files)
   ├─ SELinux/AppArmor (when available)
   └─ Audit logging
```

---

## Extension Points

### Custom Motion Detection

Replace `src/motion/motion_detector.py` implementation:
```python
class CustomMotionDetector(MotionDetector):
    def detect(self, frame):
        # Your algorithm here
        return confidence_score
```

### Custom Storage Backend

Implement storage interface:
```python
class CloudStorageBackend:
    def save_recording(self, filepath, metadata):
        # Upload to cloud storage
        pass
```

### Custom Notifications

Add to notification queue:
```python
notify_webhook(
    event_id="evt_xxx",
    confidence=0.94,
    webhook_url="https://example.com/alerts"
)
```

---

## Troubleshooting Architecture Issues

### High CPU Usage
1. Check if motion detection sensitivity is too low (frequent false positives)
2. Verify camera frame rate isn't exceeding device capability
3. Profile with `cProfile` to identify bottleneck
4. Switch to lite mode if on Pi Zero 2W

### Memory Leaks
1. Check for unclosed file handles: `lsof -p $(pgrep -f main.py)`
2. Monitor `free -h` over time while running
3. Check for unbounded queue growth in logs
4. Restart service if memory grows continuously

### Stream Dropping
1. Verify network bandwidth available
2. Check for CPU throttling due to thermal limits
3. Lower MJPEG quality setting
4. Reduce frame rate if high FPS not needed

---

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production setup recommendations.
