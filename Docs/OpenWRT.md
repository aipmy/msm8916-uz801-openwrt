# OpenWrt Flashing & Recovery

## 1. Automated One-Command Flashing

The fastest way to install OpenWrt with all hardware fixes applied:

### For Board JZ0145 (New 2026 Revision):
```bash
python3 flasher.py --flash-openwrt --board 1 --skip-backup
```

### For Board FY_UZ801 (Classic Revision):
```bash
python3 flasher.py --flash-openwrt --board 2
```

---

## 2. What Flasher Does Automatically
1. **Device Detection**: Detects whether the dongle is in Android ADB or EDL 9008 mode. If in ADB, reboots it automatically to EDL.
2. **NVRAM Backup**: Dumps calibration partitions (`fsc`, `fsg`, `modemst1`, `modemst2`, `modem`, `persist`, `sec`) to preserve original IMEI and RF calibrations.
3. **Partition Table**: Writes clean OpenWrt GPT table.
4. **Bootloader**: Flashes `sbl1.mbn`, `tz.mbn`, `rpm.mbn`, `hyp.mbn`, and `aboot.mbn`.
5. **Kernel & System**: Flashes patched `boot.img` and pre-configured SquashFS rootfs (`system.img`).
6. **Overlay Reset**: Clears `rootfs_data` for a fresh first-boot experience.
7. **NVRAM Restore**: Restores your dongle's unique IMEI and radio calibration data.
8. **Reboot**: Sends reset signal to boot directly into OpenWrt.

---

## 3. First Boot & Network Access

- **Gateway URL**: `http://192.168.1.1`
- **SSH Host**: `192.168.1.1`
- **Username**: `root`
- **Password**: *(None / Blank)*

To verify modem status via SSH:
```bash
mmcli -m 0
```
Or check network interface:
```bash
ifstatus modem
```
