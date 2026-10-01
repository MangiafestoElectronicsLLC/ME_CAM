#!/bin/bash
set -euo pipefail

STAGE_DIR="${1:?usage: install_pi_agent.sh STAGE_DIR}"
INSTALL_DIR="/opt/me_cam"
CONFIG_FILE="/etc/me_cam.conf"
SERVICE_FILE="/etc/systemd/system/me_cam.service"
REQUIRED_FILES="me_cam_agent.py auto_update.py power_manager.py config_manager.py hardware_detect.py audio_recorder.py offline_queue.py encryptor.py"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer with sudo."
    exit 1
fi
if [ ! -f "$STAGE_DIR/me_cam.conf" ]; then
    echo "Missing staged device configuration."
    exit 1
fi
if ! grep -q 'Motion recording failed; suppressing clipless alert' "$STAGE_DIR/me_cam_agent.py"; then
    echo "The staged agent is missing the clipless-motion fix; refusing to install."
    exit 1
fi
for file in $REQUIRED_FILES; do
    if [ ! -f "$STAGE_DIR/$file" ]; then
        echo "Missing staged agent file: $file"
        exit 1
    fi
    python3 -m py_compile "$STAGE_DIR/$file"
done
if [ ! -f "$STAGE_DIR/me_cam.service" ]; then
    echo "Missing staged systemd service."
    exit 1
fi

apt-get update
apt-get install -y python3 python3-picamera2 python3-opencv python3-numpy \
    python3-requests python3-psutil python3-cryptography alsa-utils ffmpeg \
    libcamera-apps

install -d -m 0755 "$INSTALL_DIR/clips" "$INSTALL_DIR/snapshots" "$INSTALL_DIR/backup"
BACKUP="$INSTALL_DIR/backup/ssh_deploy_$(date +%Y%m%d_%H%M%S)"
install -d -m 0700 "$BACKUP"
if [ -f "$CONFIG_FILE" ]; then
    cp -p "$CONFIG_FILE" "$BACKUP/me_cam.conf"
fi
systemctl stop me_cam.service 2>/dev/null || true
for file in $REQUIRED_FILES; do
    cp -p "$INSTALL_DIR/$file" "$BACKUP/$file" 2>/dev/null || true
    install -m 0644 "$STAGE_DIR/$file" "$INSTALL_DIR/$file"
done
cp -p "$STAGE_DIR/me_cam.service" "$BACKUP/me_cam.service" 2>/dev/null || true
install -m 0644 "$STAGE_DIR/me_cam.service" "$SERVICE_FILE"
install -m 0600 "$STAGE_DIR/me_cam.conf" "$CONFIG_FILE"

systemctl daemon-reload
systemctl enable me_cam.service
systemctl restart me_cam.service
systemctl --no-pager --full status me_cam.service
