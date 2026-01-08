#!/bin/bash
set -e

echo "=== ME_CAM Factory Reset ==="
cd "$(dirname "$0")"

SERVICE_NAME="mecamera"

sudo systemctl stop "$SERVICE_NAME" || true

rm -rf config/config.json
rm -rf recordings/*
rm -rf exports/*

echo "Factory reset complete. Config will regenerate on next start."

sudo systemctl start "$SERVICE_NAME"
