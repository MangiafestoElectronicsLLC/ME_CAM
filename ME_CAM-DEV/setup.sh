#!/bin/bash
set -euo pipefail

echo "=== ME Camera Setup ==="

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

. /etc/os-release
if [ "${VERSION_CODENAME:-bullseye}" = "bookworm" ] || [ "${VERSION_CODENAME:-}" = "trixie" ]; then
  CAMERA_PACKAGE="rpicam-apps"
else
  CAMERA_PACKAGE="libcamera-apps"
fi

$SUDO apt update
$SUDO apt install -y python3 python3-venv python3-dev libcamera-dev "$CAMERA_PACKAGE" \
  libjpeg-dev zlib1g-dev libopenjp2-7 libtiff-dev libssl-dev libffi-dev git

cd "$(dirname "$0")"

python3 -m venv --system-site-packages venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ! python -c 'import tflite_runtime' >/dev/null 2>&1; then
  python -m pip install tflite-runtime || echo "Warning: TensorFlow Lite runtime is unavailable; AI person detection will be disabled."
fi

MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || true)"
if [[ "$MODEL" == *"Raspberry Pi 4"* || "$MODEL" == *"Raspberry Pi 5"* ]]; then
  $SUDO apt install -y build-essential cmake libopenblas-dev liblapack-dev
  if ! python -c 'import face_recognition' >/dev/null 2>&1; then
    python -m pip install face-recognition || echo "Warning: face recognition runtime installation failed; install face-recognition before enabling it."
  fi
fi

mkdir -p config recordings exports logs models

echo "=== Setup Complete ==="
echo "Run ME Camera with:"
echo "source venv/bin/activate && python3 main.py"
