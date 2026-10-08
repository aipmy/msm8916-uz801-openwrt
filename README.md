# Qualcomm MSM8916 4G LTE USB Dongles / Sticks - OpenWrt R&D Suite

A clean, modular, and reproducible OpenWrt development ecosystem, kernel patchset, and flashing toolkit for **Qualcomm Snapdragon 410 (MSM8916)** USB 4G LTE modems and dongles.

Built on upstream **OpenWrt v25.12.x (Linux Kernel 6.12)**. Cross-platform compatible with **macOS (Apple Silicon & Intel)**, **Linux**, and **Windows (WSL2 / PowerShell)**.

---

## 🎯 Target Hardware & Supported Boards

| Target Profile | Board Code / Hardware Variants | Form Factor | Verified Features |
| :--- | :--- | :--- | :--- |
| **`jz01-45-v33`** | Handsome JZ01-45-V33 (2026 Rev), Zhihe JZ01 | USB Dongle | Native LEDs, Reset Button, SIM Mux, Modem Traffic Stats |
| **`uf896` / `ufi001c`** | THWC-UF896, THWC-UFI001C, UFI001B | USB Dongle / MiFi | 4G LTE Modem, WiFi (wcn36xx), USB Gadget |
| **`fy-mf800`** | FY-MF800, MF800B, M9S | Portable 4G WiFi | LCD / Status LEDs, ModemManager |
| **`yiming-uz801v3`**| UZ801 v3.0, UZ801 classic | USB Dongle | Base reference support |

---

## 🚀 Key Improvements & Bug Fixes over Upstream

1. **Fixed BAM-DMUX Traffic Stats (0 Bytes Bug)**:
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

## 📂 Repository Structure

```text
├── configs/                   # Target diffconfigs (jz0145, mf800b, uf02, ufi001b, etc.)
│   ├── diffconfig_jz0145_complete
│   ├── diffconfig_mf800b
│   ├── diffconfig_uf02
│   └── diffconfig_ufi001b
├── patches/                   # Clean in-tree kernel & DTS patches
│   ├── dts/                   # Native board device tree files (.dts)
│   ├── kernel/                # Custom kernel modules (ledtrig-sim.c)
│   ├── 890-wwan-qcom-bam-dmux-fix-rx-tx-stats.patch
│   ├── 891-drivers-leds-add-simcard-trigger.patch
│   └── 910-arm64-dts-fix-jz0145-leds.patch
├── scripts/                   # Automated build & utility scripts
│   ├── build_in_docker.sh     # Reproducible Docker build pipeline
│   └── edl_backup.py          # Standalone partition backup utility
├── firmware/                  # Firmware storage and release binaries
│   ├── output/                # Final build artifacts (boot.img, system.img, etc.)
│   └── README.md
├── backups/                   # Storage directory for saved EFS / NVRAM dumps
├── edl/                       # Bundled EDL client & Qualcomm Firehose loader
├── flasher.py                 # Interactive cross-platform flashing utility
├── Dockerfile                 # Containerized build environment (Ubuntu 22.04)
├── docker-compose.yml         # Docker volume mount definitions
└── README.md
```

---

## 🛠️ Building Firmware via Docker

### Prerequisites
- Docker & Docker Compose installed on your host OS.
- At least 25 GB free disk space.

### Build Steps

1. **Clone this repository**:
   ```bash
   git clone https://github.com/aipmy/msm8916-uz801-openwrt.git
   cd msm8916-uz801-openwrt
   ```

2. **Run the Automated Build Pipeline**:
   ```bash
   docker compose run --rm openwrt-builder /home/builder/project/scripts/build_in_docker.sh
   ```

3. **Monitor Live Build Progress**:
   ```bash
   docker logs -f $(docker ps -q --filter ancestor=msm8916-uz801-openwrt-openwrt-builder | head -n 1)
   ```

4. **Output Binaries**:
   Artifacts will be packaged automatically into `firmware/output/`:
   - `openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-boot.img` (Kernel, DTB & lk2nd)
   - `openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-system.img` (Root Filesystem)
   - `openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-gpt_both0.bin` (Partition Table)
   - `openwrt-msm89xx-msm8916-jz01-45-v33-firmware.zip` (Signed Modem DSP Firmware)

---

## ⚡ Flashing & Unbricking Guide (macOS, Linux & Windows)

### 1. Putting the Dongle into EDL 9008 Mode
- **From ADB (OEM / Android Firmware)**:
  ```bash
  adb reboot edl
  ```
- **From Fastboot**:
  ```bash
  fastboot oem reboot-edl
  ```
- **Hardware Testpoint (Unbricking)**:
  Short the physical EDL test points on the PCB to ground while plugging the USB dongle into your computer.

### 2. Launch the Interactive Flasher
```bash
python3 flasher.py
```

The menu provides:
- **Option 1**: Partition Table Diagnosis (`printgpt`)
- **Option 4**: Backup Critical Radio & IMEI Partitions (`modemst1`, `modemst2`, `fsg`, `fsc`)
- **Option 5 / 6**: Full eMMC Dump (4GB Raw / Partition by Partition)
- **Option 7**: Flash OpenWrt Firmware (Safe auto-backup + GPT + Kernel + RootFS)
- **Option 8**: Restore Radio Partitions

---

## 🌐 Default Credentials & Network Configuration

- **LuCI Web UI**: `http://192.168.1.1`
- **SSH Access**: `ssh root@192.168.1.1` (No password by default)
- **Modem Interface**: Protocol `ModemManager`, Device `qcom-soc`
- **Default Wi-Fi**: OpenWrt (Disabled by default, configure in **Network -> Wireless**)

---

## 📦 Built-in Packages & Features

Our standard firmware image is pre-loaded with essential networking, monitoring, and modem utilities out of the box:

### 1. Cellular & Modem Stack
- **ModemManager & libqmi / libmbim**: Automatic connection management for Qualcomm Hexagon QDSP6 modem subsystem (`wwan0`).
- **5G/4G Modem Status Dashboard**: Real-time signal strength (RSRP, RSRQ, RSSI), cell ID, carrier bands, and SMS inbox manager.
- **BAM-DMUX Traffic Accounting**: In-tree kernel counter fix for real-time RX/TX data metrics.

### 2. Networking & Diagnostics
- **LuCI Web Interface**: Modern OpenWrt web UI with Bootstrap & Argon mobile-responsive support.
- **kmod-ledtrig-netdev & ledtrig-sim**: Kernel-level hardware LED triggers configurable directly via **System -> LED Configuration**.
- **Diagnostic Tools**: `curl`, `htop`, `iperf3`, `tcpdump`, `ethtool`.

### 3. Memory & System Optimization
- **zram-swap & kmod-zram**: In-RAM compressed swap with LZ4/ZSTD algorithm (crucial for smooth multitasking on 384MB - 512MB RAM).
- **USB Gadget Support**: NCM / RNDIS plug-and-play USB Ethernet tethering for host PC/laptop.

---

## 📜 License & Credits

- Upstream OpenWrt: GPL-2.0
- Qualcomm MSM8916 Mainline Linux Kernel: GPL-2.0
- Thanks to the open-source community contributors: `hkfuertes`, `ImMALWARE`, `akbar-npj`, and `bkerler` (edl).
