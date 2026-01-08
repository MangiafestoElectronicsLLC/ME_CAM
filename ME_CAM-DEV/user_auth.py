import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
from loguru import logger

USERS_FILE = "config/users.json"

def _ensure_users_file():
    """Create users file if it doesn't exist."""
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        default_users = {
            "admin": {
                "password_hash": generate_password_hash("admin123"),
                "pin": "1234",
                "role": "admin"
            }
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(default_users, f, indent=2)
        logger.info("[AUTH] Created default admin user (username: admin, password: admin123)")

def get_users():
    """Load all users from file."""
    _ensure_users_file()
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[AUTH] Error loading users: {e}")
        return {}

def save_users(users):
    """Save users to file."""
    try:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        logger.info("[AUTH] Users saved")
        return True
    except Exception as e:
        logger.error(f"[AUTH] Error saving users: {e}")
        return False

def user_exists(username):
    """Check if username exists."""
    users = get_users()
    return username in users

def authenticate(username, password):
    """Authenticate user with username and password."""
    users = get_users()
    if username not in users:
        return False
    
    user = users[username]
    return check_password_hash(user.get("password_hash", ""), password)

def create_user(username, password, pin="1234"):
    """Create new user."""
    if user_exists(username):
        logger.warning(f"[AUTH] User {username} already exists")
        return False
    
    users = get_users()
    users[username] = {
        "password_hash": generate_password_hash(password),
        "pin": pin,
        "role": "user"
    }
    return save_users(users)

def change_password(username, old_password, new_password):
    """Change user password."""
    if not authenticate(username, old_password):
        logger.warning(f"[AUTH] Wrong password for user {username}")
        return False
    
    users = get_users()
    users[username]["password_hash"] = generate_password_hash(new_password)
    return save_users(users)

def get_user(username):
    """Get user details."""
    users = get_users()
    return users.get(username)
