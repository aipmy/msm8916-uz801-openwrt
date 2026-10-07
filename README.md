# MSM8916 OpenWrt R&D & Flashing Toolkit

Toolkit R&D and deployment OpenWrt untuk modem/stick 4G Qualcomm Snapdragon 410 (MSM8916).

## Target Boards
- **jz01-45-v33**: Handsome / JZxxx board (prioritas R&D saat ini)
- **thwc-uf896**: UF896 boards
- **thwc-ufi001c**: UFIxxx boards
- **fy-mf800**: FY-MF800 boards

## Struktur Folder
```text
msm8916-uz801-openwrt/
├── backups/           # Backup partisi EFS (modemst1, modemst2, fsg, fsc) & QCN
├── firmware/          # Image boot.img & rootfs.img OpenWrt per board
├── packages/          # Offline package (.apk / .ipk aarch64)
├── scripts/           # Utility script (EDL dump, AT command, modem reset)
├── flasher.py         # Script flasher Python CLI
└── README.md
```

## Penggunaan Script Python (`flasher.py`)

1. Cek daftar board yang didukung:
   ```bash
   python3 flasher.py list-boards
   ```

2. Flash board `jz01-45-v33` (dry-run):
   ```bash
   python3 flasher.py flash --board jz01-45-v33 --dry-run
   ```

3. Flash board `jz01-45-v33` (live fastboot):
   ```bash
   python3 flasher.py flash --board jz01-45-v33
   ```
