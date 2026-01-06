#!/bin/bash
set -e

echo "=== ME Camera Setup (Bullseye) ==="

sudo apt update
sudo apt install -y \
python3.9 python3.9-venv python3.9-dev \
libatlas-base-dev liblapack-dev gfortran \
libjpeg-dev zlib1g-dev libopenjp2-7 libtiff-dev \
libssl-dev libffi-dev libcamera-dev libcamera-apps git

mkdir -p config recordings exports logs

if [ ! -f config/config.json ]; then
    cp config/config_default.json config/config.json
fi

python3.9 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "=== Setup Complete ==="
echo "Run ME Camera with:"
echo "source venv/bin/activate && python3 main.py"
