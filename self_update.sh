#!/bin/bash
set -e

echo "=== ME_CAM Self-Update ==="
cd "$(dirname "$0")"

SERVICE_NAME="mecamera"

if systemctl is-active --quiet "$SERVICE_NAME"; then
  sudo systemctl stop "$SERVICE_NAME"
fi

git fetch origin
git checkout DEV
git pull origin DEV

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

sudo systemctl daemon-reload
sudo systemctl start "$SERVICE_NAME"

echo "=== Update complete ==="
