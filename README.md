# msm8916-uz801-openwrt

> **All-in-One Flasher, EDL 9008 Recovery, Multi-Board DTB Patching, and OpenWrt R&D Suite for Qualcomm Snapdragon 410 (MSM8916) 4G LTE USB Modems & Dongles.**

[![GitHub Stars](https://img.shields.io/github/stars/aipmy/msm8916-uz801-openwrt?style=flat-square)](https://github.com/aipmy/msm8916-uz801-openwrt/stargazers)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Qualcomm%20MSM8916%20%28Snapdragon%20410%29-orange.svg?style=flat-square)]()
[![OpenWrt](https://img.shields.io/badge/OpenWrt-v25.12.5-green.svg?style=flat-square)](https://openwrt.org)
[![Kernel](https://img.shields.io/badge/Linux%20Kernel-6.12.94-brightgreen.svg?style=flat-square)](https://kernel.org)

---

## 📑 Quick Links & Documentation

- [Introduction & Board Architecture](docs/Introduction.md)
- [Hardware Pinout & Flashing Guide](Docs/HARDWARE_AND_FLASHING.md)
- [Firmware Dump and EFS/NVRAM Restore](docs/Firmware-Dump-and-Restore.md)
- [Customizing & Docker Build Pipeline](docs/Build-Guide.md)
- [Hardware Modifications & SIM Pinouts](docs/Modifications.md)
- [OpenWrt Configuration & Modem Setup](docs/OpenWRT.md)
- [EDL 9008 Recovery & Unbricking](docs/Recovery.md)
- [Troubleshooting Common Issues](docs/Troubleshooting.md)

---

## 🎯 Target Hardware & Supported Boards

| Target Profile | Board Code / Hardware Variants | Form Factor | Verified Features |
| :--- | :--- | :--- | :--- |
| **`jz01-45-v33`** | Handsome JZ01-45-V33 (2026 Rev), Zhihe JZ01 | USB Dongle | Native LEDs (R25, G6, B7), Reset Button (37), SIM Mux (22/23/1/52), BAM-DMUX Traffic Stats, Proton2025, 5G/4G App |
| **`generic-uf02`** | Generic 250605 V0S / UF02 Dongle | USB Dongle | 4G LTE Modem, WiFi (wcn36xx), USB Gadget, Proton2025, 5G/4G App |
| **`yiming-uz801v3`** | YiMing UZ801 v3.0 | USB Dongle | 4G LTE Modem, WiFi (wcn36xx), USB Gadget, Proton2025, 5G/4G App |
| **`uf896` / `ufi001c`** | THWC-UF896, THWC-UFI001C, UFI001B | USB Dongle / MiFi | 4G LTE Modem, WiFi (wcn36xx), USB Gadget (RNDIS/NCM) |
| **`fy-mf800`** | FY-MF800, MF800B, M9S | Portable 4G WiFi | LCD / Status LEDs, ModemManager, SIM Switch |
| **`yiming-uz801v3`**| UZ801 v3.0, UZ801 classic | USB Dongle | Base reference support |

---

## 🚀 Key Improvements & Bug Fixes over Upstream

1. **Fixed BAM-DMUX Traffic Accounting (0 Bytes Bug)**:
   - Upstream Linux kernel does not update netdev packet counters for Qualcomm BAM-DMUX.
   - Integrated kernel patch using `DEV_STATS_INC` and `DEV_STATS_ADD` ensures accurate real-time RX/TX throughput monitoring in LuCI Web UI and `/proc/net/dev`.
2. **Accurate Hardware Device Tree for JZ01-45-V33**:
   - Corrected physical GPIO pinouts verified directly against live hardware:
     - **Red LED (`red:power`)**: GPIO 25 (Active-High)
     - **Green LED (`green:wan`)**: GPIO 6 (Active-High, `default-state = "off"`)
     - **Blue LED (`blue:wlan`)**: GPIO 7 (Active-High)
     - **Reset Button**: GPIO 37 (Active-Low)
     - **SIM Multiplexer**: GPIO 22, 23 (LOW), GPIO 1 (HIGH), SIM Detect (GPIO 52)
3. **Native Kernel LED Triggers (`ledtrig-sim` & `netdev`)**:
   - In-tree C kernel trigger driver (`ledtrig-sim.c`) providing native status triggers: SIM Card inserted, searching, or missing.
   - Native `netdev` trigger for dynamic data traffic blinking on `wwan0` (4G) and `br-lan` (WiFi/USB Client).
4. **All-in-One Flasher & EFS Backup Toolkit (`flasher.py`)**:
   - Standalone, interactive CLI with built-in EDL 9008 protocol and Qualcomm Firehose loader.
   - Automatically safeguards critical NVRAM/EFS radio partitions (`modemst1`, `modemst2`, `fsg`, `fsc`, `persist`).

---

## 📦 Built-in Packages & Features

Our standard firmware image is pre-loaded with essential networking, monitoring, and modem utilities out of the box:

### 1. Cellular & Modem Stack
- **ModemManager & libqmi / libmbim**: Automatic connection management for Qualcomm Hexagon QDSP6 modem subsystem (`wwan0`).
- **5G/4G Modem Status Dashboard**: Real-time signal strength (RSRP, RSRQ, RSSI), cell ID, carrier bands, and SMS inbox manager (`luci-app-5gmodem`).
- **Proton Quick Status Bar**: Persistent interactive bar under the topbar displaying SIM/Carrier status, SMS counter, temperature, CPU/RAM, and client count directly on all pages.
- **BAM-DMUX Traffic Accounting**: In-tree kernel counter fix for real-time RX/TX data metrics.

### 2. Networking & Diagnostics
- **LuCI Web Interface**: Modern OpenWrt web UI with Bootstrap & Argon mobile-responsive support.
- **kmod-ledtrig-netdev & ledtrig-sim**: Kernel-level hardware LED triggers configurable directly via **System -> LED Configuration**.
- **Diagnostic Tools**: `curl`, `htop`, `iperf3`, `tcpdump`, `ethtool`.

### 3. Memory & System Optimization
- **zram-swap & kmod-zram**: In-RAM compressed swap with LZ4/ZSTD algorithm (crucial for smooth multitasking on 384MB - 512MB RAM).
- **USB Gadget Support**: NCM / RNDIS plug-and-play USB Ethernet tethering for host PC/laptop.

---

## 🛠️ Prerequisites & Setup

Ensure your host OS has Python 3 and USB drivers installed:

- **Windows**:
  1. Install [Python 3](https://www.python.org/downloads/) (Check *"Add Python to PATH"* during installation).
  2. Install [Qualcomm HS-USB QDLoader 9008 Driver](https://gsmusbdriver.com/qualcomm-hs-usb-qdloader-9008) or use **Zadig** to install `WinUSB` or `libusb-win32` driver for VID `05C6` PID `9008`.
- **macOS (Apple Silicon & Intel)**:
  ```bash
  brew install libusb python3
  ```
- **Linux (Ubuntu / Debian / Arch / Fedora)**:
  ```bash
  sudo apt update && sudo apt install -y python3 python3-venv python3-pip libusb-1.0-0-dev
  ```

---

## ⚡ Quick Start & Flashing

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/aipmy/msm8916-uz801-openwrt.git
cd msm8916-uz801-openwrt

python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r edl/requirements.txt
```

### 2. Put Dongle into EDL 9008 Mode
- **From ADB**: `adb reboot edl`
- **From Fastboot**: `fastboot oem reboot-edl`
- **Hardware Testpoint**: Hold the physical reset button or short test points to GND while connecting to USB.

### 3. Run Interactive Flasher
```bash
python3 flasher.py
```

> For step-by-step flashing options (Interactive CLI, Fastboot manual commands, and EDL 9008 emergency unbrick), consult the [Flashing & Firmware Guide](Docs/FLASHING_GUIDE.md).

---

## 🏗️ Docker Build Pipeline (Reproducible Build)

To compile the entire OpenWrt firmware from scratch:

```bash
docker compose run -d --name openwrt-msm8916-build openwrt-builder bash -c "
sudo apt-get update && sudo apt-get install -y bc && \
/home/builder/project/scripts/build_in_docker.sh
"
```

Monitor live build progress anytime:
```bash
docker logs -f openwrt-msm8916-build
```

---

## 📜 Credits & Acknowledgements

Special thanks to the researchers and open-source pioneers:
- **[B. Kerler (@bkerler)](https://github.com/bkerler/edl)** - For the `edl` client toolset.
- **[AlienWolfX (@AlienWolfX)](https://github.com/AlienWolfX/UZ801-USB-MODEM)** - For hardware schematics and reverse engineering.
- **[hkfuertes (@hkfuertes)](https://github.com/hkfuertes/msm8916-openwrt)** - For modern OpenWrt target definitions.
- **[ImMALWARE (@ImMALWARE)](https://github.com/ImMALWARE/uz801-openwrt)** - For the BAM-DMUX stats kernel counter logic.
- **[akbar-npj (@akbar-npj)](https://github.com/akbar-npj/msm8916-openwrt)** - For multi-board diffconfigs and documentation.

## License

This repository is open-source software licensed under the [MIT License](LICENSE).

<p align="center">Maintained with ❤️ by <b><a href="https://github.com/aipmy">@aipmy</a></b></p>
