# Contributing to ME_CAM

Thank you for your interest in contributing to ME_CAM! This document provides guidelines for participating in the project.

## Code of Conduct

- Be respectful and inclusive
- Avoid discriminatory language
- Focus on constructive feedback
- Report violations to maintainers

## How to Contribute

### Reporting Bugs

1. **Check existing issues** - Search to avoid duplicates
2. **Create detailed issue** with:
   - Device model (Pi Zero 2W, Pi 4, etc.)
   - OS version (Bullseye, Bookworm, etc.)
   - Exact error message and logs
   - Steps to reproduce
   - Expected vs actual behavior

### Proposing Features

1. **Discuss first** - Open an issue to gauge interest
2. **Explain use case** - Why this feature matters
3. **Consider constraints** - Pi Zero 2W compatibility, battery impact
4. **Propose implementation** - High-level approach

### Submitting Code

#### Setup Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/ME_CAM-DEV.git
cd ME_CAM-DEV

# Create feature branch
git checkout -b feature/my-feature

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Code Standards

**Style & Formatting**
```bash
# Format with Black
black src/ web/ tests/ --line-length=100

# Check with Flake8
flake8 src/ web/ tests/ --max-line-length=100 --ignore=E203,W503

# Type checking with mypy
mypy src/ --ignore-missing-imports
```

**Naming Conventions**
- Classes: `PascalCase` (e.g., `MotionDetector`)
- Functions: `snake_case` (e.g., `get_device_status`)
- Constants: `UPPER_CASE` (e.g., `DEFAULT_PORT`)
- Private methods: `_snake_case` (e.g., `_validate_input`)

**Documentation**
```python
def process_motion_frame(frame, sensitivity: int = 50) -> bool:
    """
    Detect motion in captured frame using background subtraction.
    
    Args:
        frame: Input image array from camera
        sensitivity: Detection threshold 1-100 (default: 50)
        
    Returns:
        bool: True if motion detected above threshold
        
    Raises:
        ValueError: If sensitivity outside range 1-100
        
    Example:
        >>> motion_detected = process_motion_frame(captured_frame, sensitivity=75)
    """
```

#### Testing

**Write Tests for New Code**
```bash
# Create test file (e.g., tests/test_new_feature.py)
pytest tests/test_new_feature.py -v

# Run full test suite
pytest tests/ -v --cov=src

# Check coverage report
coverage report -m
```

**Security Test Template**
```python
import pytest
from src.core.security_middleware import verify_csrf_token, hash_password

def test_csrf_token_validation():
    """Test that invalid CSRF tokens are rejected."""
    token = "invalid-token"
    assert not verify_csrf_token(token)

def test_password_hashing():
    """Test password hashing with non-matching passwords."""
    password = "test-password-123"
    hashed = hash_password(password)
    
    assert hashed != password
    assert hash_password(password) != hashed  # Different salts
```

**Security Testing Checklist**
- [ ] CSRF tokens generated and validated
- [ ] Sensitive data never logged
- [ ] SQL injection/command injection prevented
- [ ] Rate limiting tested
- [ ] Authentication bypass attempted and prevented
- [ ] Input validation comprehensive
- [ ] No hardcoded credentials

#### Security Checklist for All PRs

**Before submitting, verify:**
- ✅ No credentials (passwords, API keys, tokens) in code
- ✅ No device hostnames or real IP addresses
- ✅ No internal/testing URLs
- ✅ All user input validated and sanitized
- ✅ Security headers maintained
- ✅ Tests pass: `pytest tests/ -v`
- ✅ Code formatted: `black . && flake8 .`
- ✅ No new dependencies without justification
- ✅ Changelog updated if user-facing changes

#### Common Patterns

**Input Validation**
```python
from src.core.security_middleware import validate_input

# Always validate user-supplied data
device_name = validate_input(request.form.get('device_name'))
if not device_name:
    return {'status': 'error'}, 400
```

**Secure Logging**
```python
import logging

logger = logging.getLogger(__name__)

# ✅ Good - no sensitive data
logger.info(f"Device {device_id} registered")

# ❌ Bad - credentials logged
logger.info(f"Device password: {password}")
```

**Error Handling**
```python
# ✅ Good - generic user message
try:
    result = authenticate_device()
except Exception as e:
    logger.error(f"Auth failed: {e}")
    return {'status': 'error'}, 401

# ❌ Bad - leaks details
except Exception as e:
    return {'status': 'error', 'details': str(e)}, 401
```

### Submitting a Pull Request

1. **Push to fork**: `git push origin feature/my-feature`
2. **Create PR** with:
   - Clear title: `Add motion detection filtering` (not "fix bugs")
   - Detailed description of changes
   - Links to related issues
   - Any breaking changes clearly marked

3. **PR Template** (automatically shown):
```markdown
## Description
Brief summary of changes

## Type
- [ ] Bug fix
- [ ] Feature
- [ ] Security fix
- [ ] Documentation
- [ ] Performance

## Testing
- [ ] Unit tests added
- [ ] Integration tests pass
- [ ] Manual testing on Pi completed

## Security
- [ ] No credentials added
- [ ] No sensitive data leaked
- [ ] Input validation included
- [ ] Security tests pass

## Checklist
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or noted)
```

### Review Process

- **Automated checks** must pass (tests, linting, security)
- **Maintainer review** for functionality and architecture
- **Community feedback** (issues, questions)
- **CI/CD pipeline** verification on target hardware

Typical turnaround: 3-7 days for review

### Deployment

Once merged to `main`:
- Automatically tested against Pi hardware
- Tagged as release when ready
- Published to GitHub releases
- Documented in CHANGELOG

## Development Tips

### Local Hardware Testing

```bash
# SSH to Pi and pull branch
ssh pi@camera.local

# Test locally on Pi
cd ~/ME_CAM-DEV
git fetch origin feature/my-feature
git checkout feature/my-feature

# Run tests
python -m pytest tests/ -v
```

### Performance Profiling

```bash
# Using cProfile
python -m cProfile -o profile.stats main_lite.py

# Analyze
python -m pstats profile.stats
```

### Common Development Commands

```bash
# Run app locally
python main.py --debug

# Run lite mode
python main_lite.py

# Enable verbose logging
export LOG_LEVEL=DEBUG
python main.py

# Connect to specific device
MECAM_DEVICE_ID=camera-office python main.py
```

## Documentation

### Update README when:
- Adding new user-facing feature
- Changing installation steps
- Modifying configuration format

### Update API_REFERENCE.md when:
- Adding/modifying REST endpoints
- Changing request/response format
- Adding authentication requirements

### Update CHANGELOG.md when:
- Fixing bugs
- Adding features
- Making breaking changes

## Release Process

Releases are tagged with semantic versioning: `vMAJOR.MINOR.PATCH`

### Example Release PR
```markdown
# Release v3.1.0

## Changes
- Motion detection improvements
- Pi Zero 2W optimization
- 5 bug fixes

## Tests Passing
- [ ] All unit tests
- [ ] Security tests
- [ ] Pi 4B hardware test
- [ ] Pi Zero 2W hardware test

## No secrets leaked
- [ ] No credentials found
- [ ] No hostnames in docs
- [ ] No real IPs in examples
```

## Questions?

- **General questions**: Open a GitHub Discussion
- **Security issues**: See [SECURITY.md](SECURITY.md)
- **Bug reports**: Create an issue with reproduction steps
- **Feature requests**: Start with a Discussion

---

**Thank you for contributing to ME_CAM! 🎉**
