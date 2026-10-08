# Flashing & Firmware Guide — Snapdragon 410 (MSM8916) 4G LTE USB Dongles

Custom OpenWrt v25.12 (Kernel 6.12.94) optimized for Qualcomm Snapdragon 410 (MSM8916) USB LTE sticks and dongles.

---

## 📦 Supported Boards & Prebuilt Firmware

All firmware images are pre-compiled and ready to flash without compiling:

| Board Target | Hardware Description | Boot Image | System Image | Partition Table |
|---|---|---|---|---|
| **JZ01-45-V33** | Handsome JZ01-45 (LED: Red 25, Green 6, Blue 7; SIM mux: 22/23/1/52) | `openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-boot.img` | `openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-system.img` | `openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-gpt_both0.bin` |
| **Generic UF02** | 250605 V0S / UF02 Dongle | `openwrt-msm89xx-msm8916-generic-uf02-squashfs-boot.img` | `openwrt-msm89xx-msm8916-generic-uf02-squashfs-system.img` | `openwrt-msm89xx-msm8916-generic-uf02-squashfs-gpt_both0.bin` |
| **YiMing UZ801 v3** | UZ801 v3.0 LTE USB Stick | `openwrt-msm89xx-msm8916-yiming-uz801v3-squashfs-boot.img` | `openwrt-msm89xx-msm8916-yiming-uz801v3-squashfs-system.img` | `openwrt-msm89xx-msm8916-yiming-uz801v3-squashfs-gpt_both0.bin` |

---

## ✨ Features & Kernel Fixes Included

1. **Linux Kernel 6.12.94**:
   - Modern LTS mainline Qualcomm MSM8916 kernel.
2. **qcom_bam_dmux RX/TX Traffic Counter Fix**:
   - Fixes the downstream Qualcomm BAM DMUX driver bug where RX/TX remained at 0 Bytes.
3. **Hardware Pinout & Native Triggers**:
   - Native SIM status and network activity mapping.
   - LuCI-configurable LED triggers directly in Web UI.
4. **LuCI Modern Web Interface & Modem Suite**:
   - Default Theme: **Proton 2025** (`luci-theme-proton2025`).
   - Modem Dashboard: **5G/4G Cellular Manager** (`luci-app-5gmodem`).
   - Integrated utilities: `sms-tool`, `comgt`, `qmi-utils`, `mbim-utils`, `modemmanager`.

---

## ⚡ Method 1: Interactive 1-Click Flasher (Recommended)

Run the interactive flasher CLI from the root of this repository:

```bash
python3 flasher.py
```

The tool will auto-detect whether your dongle is in **EDL 9008 Mode** or **Fastboot Mode**, present a menu to choose your board target, back up critical EFS partitions (`modemst1`, `modemst2`, `fsg`, `fsc`), partition the eMMC via GPT, and flash both kernel boot and squashfs system images cleanly.

---

## ⚡ Method 2: Fastboot Manual Flashing

If your dongle is already running Android / Little Kernel (LK) fastboot:

```bash
# 1. Put device into fastboot mode
adb reboot bootloader

# 2. Navigate to firmware output directory
cd firmware/output

# 3. Flash partition table (clean install)
fastboot flash partition <target-board>-squashfs-gpt_both0.bin

# 4. Erase previous rootfs overlay data
fastboot erase rootfs_data

# 5. Flash Boot (Kernel + DTB) and System (SquashFS rootfs)
fastboot flash boot <target-board>-squashfs-boot.img
fastboot flash system <target-board>-squashfs-system.img

# 6. Reboot into OpenWrt
fastboot reboot
```

---

## ⚡ Method 3: EDL 9008 Emergency Flashing (Unbrick / Stock Recovery)

If your dongle is hard-bricked or stuck in Qualcomm HS-USB QDLoader 9008 mode:

```bash
# 1. Check EDL detection
edl /l

# 2. Backup EFS / Radio calibrations first
edl r modemst1 backups/modemst1.bin --loader=edl/loaders/MSM8916_UZ801.bin
edl r modemst2 backups/modemst2.bin --loader=edl/loaders/MSM8916_UZ801.bin
edl r fsg backups/fsg.bin --loader=edl/loaders/MSM8916_UZ801.bin
edl r fsc backups/fsc.bin --loader=edl/loaders/MSM8916_UZ801.bin

# 3. Flash GPT partition table and OpenWrt partitions
edl w partition firmware/output/<target-board>-squashfs-gpt_both0.bin --loader=edl/loaders/MSM8916_UZ801.bin
edl w boot firmware/output/<target-board>-squashfs-boot.img --loader=edl/loaders/MSM8916_UZ801.bin
edl w system firmware/output/<target-board>-squashfs-system.img --loader=edl/loaders/MSM8916_UZ801.bin

# 4. Reboot
edl reset --loader=edl/loaders/MSM8916_UZ801.bin
```

---

## 🌐 Post-Flash Network & Access

- **Default IP**: `192.168.1.1`
- **Web UI**: `http://192.168.1.1` (Theme Proton 2025)
- **SSH**: `ssh root@192.168.1.1` (No initial password, set upon first login)
- **USB Ethernet**: Dongle presents RNDIS / CDC-Ethernet gadget automatically to USB host.
- **Cellular Management**: Open LuCI -> Modem -> **5G/4G Modem** to view signal quality, tower ID, lock bands, send/read SMS, and run USSD commands.
