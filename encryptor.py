from cryptography.fernet import Fernet
import os

KEY_FILE = "key.key"

if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())

key = open(KEY_FILE, "rb").read()
cipher = Fernet(key)

def encrypt_file(path):
    with open(path, "rb") as f:
        data = f.read()
    encrypted = cipher.encrypt(data)
    out = path.replace("motion_videos", "encrypted_videos") + ".enc"
    with open(out, "wb") as f:
        f.write(encrypted)
