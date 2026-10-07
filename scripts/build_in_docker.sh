#!/bin/bash
set -e

echo "=== MSM8916 OpenWrt Clean Build Pipeline (JZ01-45) ==="

PROJECT_DIR="/home/builder/project"
BUILD_DIR="/home/builder/openwrt"

cd "$BUILD_DIR"

if [ ! -d ".git" ]; then
    echo "[1/6] Cloning fresh OpenWrt v25.12 (Kernel 6.12)..."
    TAG=$(git ls-remote --tags https://git.openwrt.org/openwrt/openwrt.git 'v25.12.*' | grep -oP 'v25\.12\.\d+$' | sort -V | tail -1 || echo "v25.12.5")
    git clone --depth 1 -b "$TAG" https://git.openwrt.org/openwrt/openwrt.git .
fi

echo "[2/6] Setup Target msm89xx & Feeds..."
if [ ! -d "target/linux/msm89xx" ]; then
    git clone --depth 1 https://github.com/hkfuertes/msm8916-openwrt.git upstream-msm
    chmod +x upstream-msm/apply_patches.sh
    ./upstream-msm/apply_patches.sh .
    mv upstream-msm/msm89xx target/linux/msm89xx
    mv upstream-msm/packages package/msm8916
    rm -rf upstream-msm
fi

echo "[3/6] Injecting Custom Kernel Drivers & Patches..."
# 1. Patch BAM-DMUX 0 Bytes RX/TX Fix
cp "$PROJECT_DIR/patches/890-wwan-qcom-bam-dmux-fix-rx-tx-stats.patch" target/linux/msm89xx/patches-6.12/ || true

# 2. Driver & Patch LED SIM Card Trigger (ledtrig-sim.c)
mkdir -p target/linux/msm89xx/files/drivers/leds/trigger/
cp "$PROJECT_DIR/patches/kernel/ledtrig-sim.c" target/linux/msm89xx/files/drivers/leds/trigger/
cp "$PROJECT_DIR/patches/891-drivers-leds-add-simcard-trigger.patch" target/linux/msm89xx/patches-6.12/ || true

# 3. Clean Device Tree JZ01-45-V33
mkdir -p target/linux/msm89xx/files/arch/arm64/boot/dts/qcom/
cp "$PROJECT_DIR/patches/dts/msm8916-handsome-jz01-45-v33.dts" target/linux/msm89xx/files/arch/arm64/boot/dts/qcom/

# 4. Kernel Config LED Triggers
cat "$PROJECT_DIR/configs/kernel-led-triggers.conf" >> target/linux/msm89xx/config-6.12

echo "[4/6] Updating Feeds..."
./scripts/feeds update -a
./scripts/feeds install -a

echo "[5/6] Applying Configuration..."
cp "$PROJECT_DIR/configs/diffconfig_jz0145_complete" .config
make defconfig

echo "[6/6] Starting Compilation..."
make download -j$(nproc)
make -j$(nproc) V=s

echo "=== BUILD COMPLETE ==="
mkdir -p "$PROJECT_DIR/firmware/output"
cp -v bin/targets/msm89xx/msm8916/*boot*.img "$PROJECT_DIR/firmware/output/" || true
cp -v bin/targets/msm89xx/msm8916/*rootfs*.img "$PROJECT_DIR/firmware/output/" || true
echo "Output tersimpan di $PROJECT_DIR/firmware/output/"
