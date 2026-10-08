# Qualcomm MSM8916 OpenWrt - Hardware & Flashing Guide

Comprehensive technical documentation for hardware pinouts, unbricking, partition tables, and flashing instructions across Windows, macOS, and Linux.

---

## 📌 Verified Board Pinout Specifications

### 1. JZ01-45-V33 (2026 Handsome Revision)
- **SoC**: Qualcomm Snapdragon 410 (MSM8916) 4x ARM Cortex-A53
- **eMMC**: 4 GB | **RAM**: 512 MB LPDDR3
- **Status LEDs**:
  - **Red LED (`red:power`)**: GPIO 25 (Active-High)
  - **Green LED (`green:wan`)**: GPIO 6 (Active-High)
  - **Blue LED (`blue:wlan`)**: GPIO 7 (Active-High)
- **Buttons**:
  - **Reset Button**: GPIO 37 (Active-Low)
- **SIM Card Routing**:
  - **SIM Multiplexer Selection**: GPIO 22 (LOW), GPIO 23 (LOW), GPIO 1 (HIGH)
  - **SIM Hotplug / Detect**: GPIO 52 (Active-High)

### 2. THWC-UF896 / THWC-UFI001C
- **Status LEDs**:
  - LED 1 (Power/Status): GPIO 25 or GPIO 0 (depends on variant)
  - LED 2 (WAN / Modem): GPIO 6 or GPIO 1
  - LED 3 (WLAN): GPIO 7 or GPIO 2
- **Reset Button**: GPIO 37 / GPIO 38

---

## 💾 Partition Layout & Critical Radio Partitions

Never format or overwrite radio partitions without a verified backup.

| Partition Name | Typical Sector / Size | Critical Function |
| :--- | :--- | :--- |
| `modemst1` | 3 MB | NVRAM / Primary EFS Data (IMEI & Calibration) |
| `modemst2` | 3 MB | NVRAM / Secondary EFS Data |
| `fsg` | 3 MB | Golden Copy / Factory Default Radio NVRAM |
| `fsc` | 1 MB | EFS Cookie & Partition Security |
| `persist` | 32 MB | Sensor calibration, Wi-Fi MAC address |
| `boot` | 64 MB | Kernel image + Device Tree + lk2nd bootloader |
| `rootfs` (`system`) | 1 GB - 2 GB | OpenWrt SquashFS root filesystem |
| `userdata` (`overlay`)| Remainder | Ext4 user writable overlay partition |

---

## 🖥️ Cross-Platform Setup & Flashing

### macOS (Apple Silicon / Intel)
1. Install Homebrew and Python dependencies:
   ```bash
   brew install libusb python3
   ```
2. Run the interactive flasher:
   ```bash
   python3 flasher.py
   ```

### Linux (Ubuntu / Debian / Arch / Fedora)
1. Add udev rules for Qualcomm EDL 9008 (`05c6:9008`):
   ```bash
   echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="05c6", ATTR{idProduct}=="9008", MODE="0666"' | sudo tee /etc/udev/rules.d/99-qualcomm-edl.rules
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
2. Run the flasher:
   ```bash
   python3 flasher.py
   ```

### Windows (WSL2 / Native PowerShell)
1. Install [Zadig](https://zadig.akeo.ie/) and replace the `QHSUSB__BULK` or `Qualcomm HS-USB QDLoader 9008` driver with **libusb-win32** or **WinUSB**.
2. Run via Python 3:
   ```powershell
   python flasher.py
   ```
