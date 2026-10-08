#!/bin/bash
set -e

echo "=== MSM8916 OpenWrt Clean Build Pipeline (JZ01-45-V33) ==="

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
# 0. Hapus patch upstream yang konflik dengan JZ01-45 LED
rm -f target/linux/msm89xx/patches/803-arm64-dts-qcom-swap-leds-uz801.patch

# 1. Patch BAM-DMUX 0 Bytes RX/TX Fix
cp -vf "$PROJECT_DIR/patches/890-wwan-qcom-bam-dmux-fix-rx-tx-stats.patch" target/linux/msm89xx/patches/

# 2. Driver & Patch LED SIM Card Trigger (ledtrig-sim.c)
mkdir -p target/linux/generic/files/drivers/leds/trigger/
cp -vf "$PROJECT_DIR/patches/kernel/ledtrig-sim.c" target/linux/generic/files/drivers/leds/trigger/
cp -vf "$PROJECT_DIR/patches/891-drivers-leds-add-simcard-trigger.patch" target/linux/msm89xx/patches/

# 3. Patch Fisik LED JZ01-45 (Merah=25, Hijau=6, Biru=7)
cp -vf "$PROJECT_DIR/patches/910-arm64-dts-fix-jz0145-leds.patch" target/linux/msm89xx/patches/

# 4. Clean Device Tree JZ01-45-V33 (default-state = "off" untuk LED hijau)
mkdir -p target/linux/msm89xx/files/arch/arm64/boot/dts/qcom/
cp -vf "$PROJECT_DIR/patches/dts/msm8916-handsome-jz01-45-v33.dts" target/linux/msm89xx/files/arch/arm64/boot/dts/qcom/

# 5. Target Device Definition JZ01-45-V33 (Clean Append jika belum ada)
if ! grep -q "Device/jz01-45-v33" target/linux/msm89xx/image/msm8916.mk; then
    sed -i '/endif/d' target/linux/msm89xx/image/msm8916.mk
    cat >> target/linux/msm89xx/image/msm8916.mk << 'EOF'

define Device/jz01-45-v33
  $(Device/msm8916)
  DEVICE_VENDOR := Generic
  DEVICE_MODEL := JZ01-45-V33
  DEVICE_DTS := qcom/msm8916-handsome-jz01-45-v33
  SUPPORTED_DEVICES := jz01-45-v33 generic,jz01-45-v33
  FILESYSTEMS := squashfs
  DEVICE_PACKAGES := wpad-basic-wolfssl rmtfs uci-usb-gadget block-mount f2fs-tools msm-firmware-dumper
endef
TARGET_DEVICES += jz01-45-v33

endif
EOF
fi

# 6. Kernel Config (netdev & simcard trigger)
sed -i 's/# CONFIG_LEDS_TRIGGER_NETDEV is not set/CONFIG_LEDS_TRIGGER_NETDEV=y/' target/linux/msm89xx/config-6.12 || true
sed -i 's/# CONFIG_LEDS_TRIGGER_SIMCARD is not set/CONFIG_LEDS_TRIGGER_SIMCARD=y/' target/linux/msm89xx/config-6.12 || true
if ! grep -q "CONFIG_LEDS_TRIGGER_NETDEV=y" target/linux/msm89xx/config-6.12; then
    echo "CONFIG_LEDS_TRIGGER_NETDEV=y" >> target/linux/msm89xx/config-6.12
fi
if ! grep -q "CONFIG_LEDS_TRIGGER_SIMCARD=y" target/linux/msm89xx/config-6.12; then
    echo "CONFIG_LEDS_TRIGGER_SIMCARD=y" >> target/linux/msm89xx/config-6.12
fi

echo "[4/6] Updating Feeds..."
git config --global --add safe.directory '*' || true
./scripts/feeds update -a
./scripts/feeds install -a

echo "[5/6] Applying Configuration..."
cp -vf "$PROJECT_DIR/configs/diffconfig_jz0145_complete" .config
make defconfig

echo "[6/6] Clean Kernel & Starting Compilation..."
rm -rf build_dir/target-aarch64_generic_musl/linux-msm89xx_msm8916/linux-6.12.94/.modules
rm -rf build_dir/target-aarch64_generic_musl/linux-msm89xx_msm8916/linux-6.12.94/vmlinux*
rm -rf build_dir/target-aarch64_generic_musl/linux-msm89xx_msm8916/linux-6.12.94/drivers/leds/trigger/ledtrig-sim.o
make -j$(nproc) target/linux/compile
make -j$(nproc) target/linux/install

echo "=== BUILD COMPLETE ==="
OUTPUT_DIR="$PROJECT_DIR/firmware/output"
mkdir -p "$OUTPUT_DIR"

OPENWRT_VER=$(cat version.buildinfo 2>/dev/null || echo "v25.12.5")
KERNEL_VER=$(cat .vermagic 2>/dev/null || echo "6.12.94")

echo "[*] Packaging firmware artifacts for OpenWrt $OPENWRT_VER (Linux $KERNEL_VER)..."
cp -vf bin/targets/msm89xx/msm8916/*jz01-45-v33* "$OUTPUT_DIR/" || true

echo "=== FIRMWARE OUTPUT ==="
ls -lh "$OUTPUT_DIR"/*jz01-45-v33*
echo "Output tersimpan di $OUTPUT_DIR"

