#!/bin/bash

# Fix Bullseye apt repositories for Pi Zero 2W
# Bullseye repos moved to archive.raspberrypi.org - this script fixes it

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     ME_CAM Bullseye Repo Fix for Pi Zero 2W (Jan 21, 2026)    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Fix sources.list for archived Bullseye
echo "🔧 Step 1: Fixing apt sources for Bullseye (archived)..."
sudo tee /etc/apt/sources.list > /dev/null << 'EOF'
deb http://archive.raspberrypi.org/debian bullseye main contrib non-free rpi
deb http://archive.raspberrypi.org/debian bullseye-updates main contrib non-free rpi
deb http://security.debian.org/debian-security bullseye-security main contrib non-free
EOF

echo "✅ Sources fixed"
echo ""

# Step 2: Fix any broken sources.list.d entries
echo "🔧 Step 2: Fixing additional repo sources..."
if [ -d /etc/apt/sources.list.d ]; then
    for file in /etc/apt/sources.list.d/*.list; do
        if [ -f "$file" ]; then
            sudo sed -i 's|https://raspberrypi.org/debian|http://archive.raspberrypi.org/debian|g' "$file"
            sudo sed -i 's|http://raspberrypi.org/debian|http://archive.raspberrypi.org/debian|g' "$file"
        fi
    done
fi
echo "✅ Additional repos fixed"
echo ""

# Step 3: Update apt cache
echo "📥 Step 3: Running apt update..."
sudo apt update
if [ $? -ne 0 ]; then
    echo "❌ apt update failed - trying with clean cache"
    sudo apt clean
    sudo apt update
fi
echo "✅ apt update complete"
echo ""

# Step 4: Upgrade system
echo "⬆️  Step 4: Upgrading system packages..."
sudo apt upgrade -y
echo "✅ System upgraded"
echo ""

# Step 5: Install essential dependencies
echo "📦 Step 5: Installing essential dependencies..."
sudo apt install -y \
    git \
    python3-pip \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    build-essential
echo "✅ Dependencies installed"
echo ""

# Step 6: Install GObject Introspection (for GUI tools if needed)
echo "📦 Step 6: Installing GObject Introspection..."
sudo apt install -y gir1.2-glib-2.0 python3-gi
echo "✅ GObject Introspection installed"
echo ""

# Step 7: Install camera libraries for Pi Zero 2W
echo "📦 Step 7: Installing camera dependencies..."
sudo apt install -y \
    libcamera0 \
    libcamera-tools \
    libatlas-base-dev \
    libjasper-dev
echo "✅ Camera libraries installed"
echo ""

# Step 8: Verify Python3 packages work
echo "✅ Step 8: Testing Python3 imports..."
python3 -c "import gi; print('✅ GObject Introspection works')" 2>/dev/null || echo "⚠️  GI may need manual install"
python3 -c "import pip; print('✅ pip3 works')" && echo "✅ pip3 verified"
echo ""

# Step 9: Ready for ME_CAM installation
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                      ✅ READY TO INSTALL ME_CAM               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  cd ~"
echo "  git clone https://github.com/MangiafestoElectronicsLLC/ME_CAM-DEV.git"
echo "  cd ME_CAM-DEV"
echo "  python3 -m venv venv"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo ""
