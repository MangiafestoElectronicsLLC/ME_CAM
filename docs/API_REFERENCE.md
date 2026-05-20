# ME_CAM API Reference

Complete REST API documentation for ME_CAM device endpoints.

## Authentication

All requests require an enrollment key (bearer token) or enrollment code.

```bash
# Using enrollment key
curl -H "Authorization: Bearer your-enrollment-key" \
  https://camera.local:8443/api/status

# Using enrollment code (first-time setup)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"enrollment_code": "ABC123"}' \
  https://camera.local:8443/api/enroll
```

## Base URL

- **HTTP**: `http://camera.local:8080`
- **HTTPS**: `https://camera.local:8443`

Replace `camera.local` with device hostname or IP address.

---

## System Endpoints

### GET /api/status

Get current device status and metrics.

**Request**
```bash
curl -H "Authorization: Bearer token" https://camera.local:8443/api/status
```

**Response (200 OK)**
```json
{
  "device_id": "camera-001",
  "device_name": "Office Camera",
  "status": "operational",
  "firmware_version": "3.0.0",
  "uptime_seconds": 86400,
  "timestamp": "2024-05-20T14:30:00Z",
  "camera": {
    "model": "IMX519",
    "resolution": "1920x1440",
    "framerate": 30,
    "streaming": true
  },
  "system": {
    "cpu_temp_celsius": 45.2,
    "memory_mb_used": 185,
    "memory_mb_total": 1024,
    "storage_gb_used": 8.5,
    "storage_gb_total": 16,
    "uptime_hours": 24.0
  },
  "battery": {
    "percentage": 87,
    "voltage": 4.18,
    "current_ma": 450,
    "health": "good",
    "estimated_hours": 8.5
  }
}
```

**Error Responses**
- `401 Unauthorized` - Invalid or missing token
- `403 Forbidden` - Insufficient permissions

---

### GET /api/health

Lightweight health check (no authentication required during setup).

**Request**
```bash
curl https://camera.local:8443/api/health
```

**Response (200 OK)**
```json
{
  "status": "healthy",
  "camera_ready": true,
  "storage_available": true,
  "network_connected": true
}
```

---

## Camera Endpoints

### GET /api/stream

Live MJPEG stream.

**Request**
```bash
curl -O --output-document stream.mjpeg \
  -H "Authorization: Bearer token" \
  https://camera.local:8443/api/stream
```

**Response**
- `200 OK` - MJPEG video stream begins
- `206 Partial Content` - Seeking to specific timestamp
- `401 Unauthorized` - Authentication failed

**Query Parameters**
- `quality` - `low`, `medium`, `high` (default: auto-detect)
- `framerate` - `5`, `15`, `30` (fps, default: 15)

---

### GET /api/snapshot

Capture single frame as JPEG.

**Request**
```bash
curl -O snapshot.jpg \
  -H "Authorization: Bearer token" \
  https://camera.local:8443/api/snapshot
```

**Response**
- `200 OK` - JPEG image data
- `503 Service Unavailable` - Camera not ready

---

## Recording Endpoints

### GET /api/recordings

List all recorded video files.

**Request**
```bash
curl -H "Authorization: Bearer token" \
  https://camera.local:8443/api/recordings?days=7
```

**Response (200 OK)**
```json
{
  "recordings": [
    {
      "filename": "recording_2024-05-20_14-30-00.mp4",
      "timestamp": "2024-05-20T14:30:00Z",
      "duration_seconds": 600,
      "size_mb": 45.2,
      "trigger": "motion",
      "url": "/api/recordings/download/recording_2024-05-20_14-30-00.mp4"
    }
  ],
  "total_count": 45,
  "total_size_mb": 2048
}
```

**Query Parameters**
- `days` - Recordings from last N days (default: 7)
- `limit` - Maximum results (default: 100)
- `offset` - Pagination offset (default: 0)

---

### GET /api/recordings/download/:filename

Download specific recording.

**Request**
```bash
curl -O -H "Authorization: Bearer token" \
  https://camera.local:8443/api/recordings/download/recording_2024-05-20_14-30-00.mp4
```

**Response**
- `200 OK` - Video file begins streaming
- `404 Not Found` - Recording not found
- `416 Range Not Satisfiable` - Seeking beyond file

---

### POST /api/recording/start

Start manual recording.

**Request**
```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "duration_seconds": 60,
    "quality": "high"
  }' \
  https://camera.local:8443/api/recording/start
```

**Response (202 Accepted)**
```json
{
  "status": "recording_started",
  "duration_seconds": 60,
  "expected_completion": "2024-05-20T14:31:00Z"
}
```

**Query Parameters**
- `duration_seconds` - Recording length (default: 60, max: 3600)
- `quality` - `low`, `medium`, `high` (default: high)

---

### POST /api/recording/stop

Stop active recording.

**Request**
```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  https://camera.local:8443/api/recording/stop
```

**Response (200 OK)**
```json
{
  "status": "recording_stopped",
  "duration_seconds": 45,
  "filename": "recording_2024-05-20_14-30-00.mp4",
  "size_mb": 25.3
}
```

---

## Motion & Events

### GET /api/events

List motion events and alerts.

**Request**
```bash
curl -H "Authorization: Bearer token" \
  'https://camera.local:8443/api/events?hours=24&limit=50'
```

**Response (200 OK)**
```json
{
  "events": [
    {
      "event_id": "evt_20240520_143000",
      "timestamp": "2024-05-20T14:30:00Z",
      "event_type": "motion",
      "confidence": 0.94,
      "thumbnail_url": "/api/events/evt_20240520_143000/thumbnail",
      "recording_url": "/api/recordings/download/recording_2024-05-20_14-30-00.mp4"
    }
  ],
  "total_count": 12,
  "period_hours": 24
}
```

**Query Parameters**
- `hours` - Events from last N hours (default: 24, max: 720)
- `limit` - Maximum results (default: 50)
- `event_type` - Filter by type: `motion`, `manual`, `system` (default: all)

---

### GET /api/events/:event_id/thumbnail

Get motion event thumbnail.

**Request**
```bash
curl -O -H "Authorization: Bearer token" \
  https://camera.local:8443/api/events/evt_20240520_143000/thumbnail
```

**Response**
- `200 OK` - JPEG thumbnail image

---

### POST /api/motion/configure

Update motion detection settings.

**Request**
```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "sensitivity": 75,
    "enabled": true,
    "record_on_motion": true,
    "min_duration_ms": 1000
  }' \
  https://camera.local:8443/api/motion/configure
```

**Response (200 OK)**
```json
{
  "status": "configured",
  "sensitivity": 75,
  "enabled": true,
  "record_on_motion": true
}
```

**Parameters**
- `sensitivity` - Detection threshold 1-100 (default: 50)
- `enabled` - Enable/disable motion detection (default: true)
- `record_on_motion` - Auto-record on motion (default: true)
- `min_duration_ms` - Minimum event duration (default: 500)

---

## Configuration Endpoints

### GET /api/config

Get current device configuration.

**Request**
```bash
curl -H "Authorization: Bearer token" \
  https://camera.local:8443/api/config
```

**Response (200 OK)**
```json
{
  "device": {
    "device_name": "Office Camera",
    "hostname": "camera-office",
    "location": "Building A"
  },
  "network": {
    "port": 8080,
    "https_port": 8443,
    "https_enabled": true
  },
  "recording": {
    "retention_days": 30,
    "quality": "720p",
    "motion_detection": true
  },
  "security": {
    "https_enabled": true,
    "auto_logout_minutes": 60,
    "password_min_length": 8
  }
}
```

---

### POST /api/config

Update device configuration.

**Request**
```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "New Office Camera",
    "recording": {
      "retention_days": 45
    }
  }' \
  https://camera.local:8443/api/config
```

**Response (200 OK)**
```json
{
  "status": "updated",
  "updated_fields": ["device_name", "recording.retention_days"]
}
```

---

## Storage Management

### GET /api/storage

Get storage statistics and cleanup info.

**Request**
```bash
curl -H "Authorization: Bearer token" \
  https://camera.local:8443/api/storage
```

**Response (200 OK)**
```json
{
  "total_gb": 16,
  "used_gb": 8.5,
  "free_gb": 7.5,
  "usage_percent": 53,
  "retention_days": 30,
  "estimated_cleanup_days": 5,
  "cleanup_enabled": true,
  "cleanup_threshold_percent": 85
}
```

---

### POST /api/storage/cleanup

Manually trigger storage cleanup.

**Request**
```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "days_to_keep": 7
  }' \
  https://camera.local:8443/api/storage/cleanup
```

**Response (202 Accepted)**
```json
{
  "status": "cleanup_started",
  "estimated_freed_mb": 1024
}
```

---

## Authentication & Enrollment

### POST /api/enroll

Enroll device with enrollment code.

**Request**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "enrollment_code": "ABC123XYZ",
    "device_name": "My Camera",
    "location": "Home"
  }' \
  https://camera.local:8443/api/enroll
```

**Response (200 OK)**
```json
{
  "status": "enrolled",
  "enrollment_key": "key_xxx...yyy",
  "expires_days": 365
}
```

---

### POST /api/auth/login

Authenticate and get session token.

**Request**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure-password"
  }' \
  https://camera.local:8443/api/auth/login
```

**Response (200 OK)**
```json
{
  "status": "authenticated",
  "token": "session-token-xxx",
  "expires_seconds": 3600
}
```

**Error Responses**
- `401 Unauthorized` - Invalid credentials
- `429 Too Many Requests` - Rate limited

---

## Error Responses

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Descriptive error message",
  "error_code": "INVALID_INPUT",
  "details": {}
}
```

### Common HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 202 | Accepted | Request queued for processing |
| 400 | Bad Request | Invalid parameters or malformed JSON |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error (check logs) |
| 503 | Service Unavailable | Camera not ready or system overload |

---

## Rate Limiting

Requests are rate-limited to prevent abuse:

- **General traffic**: 100 requests per minute
- **Login attempts**: 5 requests per minute
- **File downloads**: No limit (whole files)

Rate limit headers included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

When rate limited (429 response), retry after the `Retry-After` header duration.

---

## CORS & Security Headers

All responses include security headers:

```
Content-Type: application/json; charset=utf-8
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

CORS is only enabled for trusted origins configured in device settings.

---

## Pagination

Large result sets use cursor-based pagination:

**Request**
```bash
curl 'https://camera.local:8443/api/recordings?limit=50&offset=100'
```

**Response**
```json
{
  "data": [...],
  "pagination": {
    "limit": 50,
    "offset": 100,
    "total": 250,
    "has_more": true,
    "next_offset": 150
  }
}
```

---

## Client Libraries

### Python
```python
import requests

class MeCAMClient:
    def __init__(self, device_url, enrollment_key):
        self.base_url = device_url
        self.headers = {'Authorization': f'Bearer {enrollment_key}'}
    
    def get_status(self):
        resp = requests.get(f'{self.base_url}/api/status', headers=self.headers)
        return resp.json()

client = MeCAMClient('https://camera.local:8443', 'your-key')
print(client.get_status())
```

### cURL
```bash
TOKEN="your-enrollment-key"
BASE_URL="https://camera.local:8443"

# Get status
curl -H "Authorization: Bearer $TOKEN" $BASE_URL/api/status

# Get stream
curl -H "Authorization: Bearer $TOKEN" $BASE_URL/api/stream > stream.mjpeg
```

---

## Webhook Callbacks (v3.1+)

Configure webhooks for motion events:

```bash
curl -X POST \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://example.com/motion-alerts",
    "events": ["motion"],
    "retry_attempts": 3
  }' \
  https://camera.local:8443/api/webhooks/register
```

---

**Questions?** See [README.md](README.md) or report issues at [GitHub Issues](https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV/issues).
