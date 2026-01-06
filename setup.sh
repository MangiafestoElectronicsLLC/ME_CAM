#!/bin/bash
set -e

echo "=== ME Camera Setup Script (Pi Zero 2 W) ==="

# Update system
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev \
    libatlas-base-dev liblapack-dev gfortran \
    libjpeg-dev zlib1g-dev libopenjp2-7 libtiff-dev \
    libssl-dev libffi-dev libcamera-dev libcamera-apps git

# Create folders
mkdir -p config recordings exports logs

# Copy default config if missing
if [ ! -f config/config.json ]; then
    cp config/config_default.json config/config.json
fi

# Create Python 3.9 venv
echo "Creating Python 3.9 virtual environment..."
python3.9 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "=== Setup Complete ==="
echo "Run ME Camera with:"
echo "source venv/bin/activate && python3 main.py"
