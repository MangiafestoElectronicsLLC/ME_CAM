import qrcode
import io
from loguru import logger

def generate_qr_code(data: str, version=1, box_size=10, border=2):
    """Generate QR code and return as base64 image."""
    try:
        qr = qrcode.QRCode(
            version=version,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        import base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    except Exception as e:
        logger.error(f"[QR] Error generating QR code: {e}")
        return None

def generate_setup_qr(hostname: str, port: int = 8080):
    """Generate QR code for setup wizard."""
    # URL format: http://hostname:port/setup
    setup_url = f"http://{hostname}.local:{port}/setup"
    return generate_qr_code(setup_url)

def generate_dashboard_qr(hostname: str, username: str, port: int = 8080):
    """Generate QR code for user dashboard."""
    # URL format: http://hostname:port/login?user=username
    dashboard_url = f"http://{hostname}.local:{port}/login"
    return generate_qr_code(dashboard_url)
