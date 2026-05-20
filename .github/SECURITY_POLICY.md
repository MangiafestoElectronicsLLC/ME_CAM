# Security Policy for ME_CAM

## Reporting a Vulnerability

**DO NOT** create a public GitHub issue to report a security vulnerability.

### Responsible Disclosure

If you discover a security issue in ME_CAM:

1. **Email the maintainer** at [security@mangiafesto.com](mailto:security@mangiafesto.com)
   - Include: description, affected versions, reproduction steps, proposed fix
   - Do not include full exploit code or credentials

2. **Allow time for remediation** before public disclosure
   - We aim to respond within 48 hours
   - Typical patch/release timeline: 1-2 weeks
   - Critical issues may be expedited

3. **Coordinated disclosure**
   - We will notify you when a patch is released
   - You're welcome to coordinate the public announcement
   - We'll acknowledge your responsible disclosure in release notes (if you consent)

### Example Email

```
Subject: Security Vulnerability in ME_CAM - [Severity]

Description:
A [briefly describe issue] vulnerability exists in ME_CAM that could allow
[explain impact].

Affected Versions:
v3.0.0, v2.2.3

Reproduction:
1. [Step 1]
2. [Step 2]
3. [Vulnerable behavior observed]

Suggested Fix:
[If you have a suggested fix, include it]

Timeline:
Please acknowledge receipt within 48 hours.
```

---

## Security Controls Implemented

### Authentication & Authorization
- ✅ Bearer token (enrollment key) validation on all protected endpoints
- ✅ CSRF token generation and strict validation
- ✅ Session-based authentication with automatic logout
- ✅ Enrollment code validation with rate limiting

### Input Validation & Output Encoding
- ✅ All user input validated against expected types
- ✅ File paths sanitized to prevent directory traversal
- ✅ JSON output properly encoded
- ✅ Special characters escaped in templates

### Network Security
- ✅ HTTPS enforced on production deployments
- ✅ Security headers (CSP, X-Frame-Options, etc.)
- ✅ CORS restricted to configured origins
- ✅ Referrer policy set to strict-origin-when-cross-origin

### Data Protection
- ✅ Passwords hashed with Werkzeug (PBKDF2)
- ✅ Sensitive data never logged
- ✅ Temporary files cleaned up after processing
- ✅ Configuration with credentials stored outside web root

### Rate Limiting
- ✅ General requests: 100/minute
- ✅ Login attempts: 5/minute
- ✅ File uploads: 10/minute
- ✅ Configurable per endpoint

### Cryptographic Controls
- ✅ Self-signed TLS certificate support
- ✅ Custom domain certificate configuration
- ✅ Enrollment key storage (no plaintext passwords)
- ✅ Secure random generation for tokens

---

## Security Testing

### Automated Scanning
- ✅ Pre-commit hooks prevent credential leaks
- ✅ GitHub Actions CI checks for obvious secrets
- ✅ Bandit SAST scanning on pull requests
- ✅ Dependency vulnerability scanning with `safety`

### Manual Testing
- ✅ CSRF bypass attempts
- ✅ SQL injection (if applicable)
- ✅ Rate limit bypass
- ✅ Authentication bypass
- ✅ Input validation bypass
- ✅ Path traversal attempts

### Test Coverage
Run security tests:
```bash
python -m pytest tests/test_security_layers.py -v --cov=src --cov-report=term-missing
```

---

## Security Best Practices for Deployers

### Before Production Deployment
1. **Change default credentials**
   ```bash
   # Set strong device password
   export MECAM_DEVICE_PASSWORD="your-secure-random-password"
   ```

2. **Rotate enrollment keys**
   - Use new enrollment codes for production devices
   - Treat enrollment keys as sensitive as passwords

3. **Enable HTTPS**
   ```json
   {
     "security": {
       "https_enabled": true,
       "https_port": 8443
     }
   }
   ```

4. **Configure reverse proxy**
   - Don't expose device directly to internet
   - Use nginx or HAProxy with rate limiting
   - Enable WAF if available

5. **Network isolation**
   - Deploy behind VPN (Tailscale, WireGuard)
   - Use private network if possible
   - Restrict to known IP addresses if public

6. **Monitoring & Logging**
   - Enable audit logging
   - Monitor for failed authentication attempts
   - Alert on security events

7. **Regular updates**
   - Subscribe to security mailing list
   - Apply patches promptly
   - Keep OS packages updated

### Handling Credentials
- ❌ Never commit credentials to git
- ❌ Never log passwords or API keys
- ❌ Never hardcode sensitive data
- ✅ Use environment variables
- ✅ Use `.env` files (add to `.gitignore`)
- ✅ Use secure credential management systems

---

## Known Limitations

### Not Implemented
- X.509 certificate pinning
- Hardware security module (HSM) support
- FIPS compliance validation
- SOC 2 Type II certification

### Threat Model Assumptions
- Deployment on trusted local network OR behind VPN
- HTTPS certificates validated by clients
- Pi hardware not physically compromised
- Systemd/init system secured with standard Linux hardening

### Out of Scope
- Protection against physical attacks
- Network-level attacks (DDoS, ARP spoofing)
- Operating system vulnerabilities
- Third-party library vulnerabilities (handled via dependency scanning)

---

## Vulnerability Disclosure Timeline

| Day | Action |
|-----|--------|
| 0 | Vulnerability reported via email |
| 1 | Maintainer acknowledges receipt |
| 7 | Patch developed and tested |
| 8 | Patch released in maintenance release |
| 8+ | Security advisory published |

Timeline varies based on severity and complexity.

---

## Security Advisory Distribution

Subscribe to security updates:
1. Watch repository for releases
2. Enable email notifications for critical releases
3. Follow [@MangiafestoLLC](https://twitter.com/MangiafestoLLC) on Twitter for announcements

---

## Version Support

| Version | Status | End of Support |
|---------|--------|-----------------|
| 3.0.x | Active | 2025-06-01 |
| 2.2.x | Maintenance | 2024-12-01 |
| 2.1.x | Deprecated | 2024-09-01 |
| < 2.0 | Unsupported | N/A |

We recommend upgrading to v3.0+ for latest security fixes.

---

## Credits

We thank security researchers who responsibly disclose vulnerabilities to help improve ME_CAM's security posture.

---

**Questions about security?** Contact [security@mangiafesto.com](mailto:security@mangiafesto.com)
