#!/bin/bash
set -e

echo "=== ME Camera Setup (Bullseye) ==="

sudo apt update
sudo apt install -y \
python3.9 python3.9-venv python3.9-dev \
libatlas-base-dev liblapack-dev gfortran \
libjpeg-dev zlib1g-dev libopenjp2-7 libtiff-dev \
libssl-dev libffi-dev libcamera-dev libcamera-apps \
libopenexr25 libilmbase25 openexr git

cd "$(dirname "$0")"

python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip

cat > requirements.txt <<EOF
Flask==2.2.5
Werkzeug==2.2.3
numpy==1.20.3
opencv-python-headless==4.5.1.48
Pillow==9.5.0
cryptography==39.0.0
psutil==5.9.5
qrcode[pil]==7.4.2
yagmail==0.15.293
pydrive2==1.19.0
tflite-runtime==2.7.0
loguru==0.7.2
EOF

pip install -r requirements.txt

mkdir -p config recordings exports logs models

if [ ! -f config/config.json ]; then
  if [ -f config/config_default.json ]; then
    cp config/config_default.json config/config.json
  else
    echo "Missing config_default.json"
  fi
fi

echo "=== Setup Complete ==="
echo "Run ME Camera with:"
echo "source venv/bin/activate && python3 main.py"
