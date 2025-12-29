import cv2, time
from encryptor import encrypt_file

cam = cv2.VideoCapture(0)
last_motion = time.time()

while True:
    ret, frame = cam.read()
    if not ret:
        continue

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (21,21), 0)

    if time.time() - last_motion > 10:
        filename = f"motion_videos/{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        encrypt_file(filename)
        last_motion = time.time()
