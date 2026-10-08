# Firmware Dump and Restore

Safely dumping and restoring eMMC firmware ensures you can always recover your dongle from any soft-brick or configuration error.

---

## 1. Entering Qualcomm EDL Mode (9008)

### Method A: Software (ADB)
If the modem is currently booted into Android with USB debugging active:
```bash
adb reboot edl
```

### Method B: Hardware Testpad / Pin Shorting
If the modem is bricked or stuck in a bootloop:
1. Locate the USB connector pins:
   - Pin 1: VBUS (5V)
   - Pin 2: D- (Data -)
   - Pin 3: D+ (Data +)
   - Pin 4: GND (Ground)
2. Bridge **D+ (Pin 3)** to **GND (Pin 4)** with a tweezer or wire.
3. Plug the modem into your computer's USB port while holding the bridge.
4. Wait 3 seconds, then release the bridge.
5. The modem will enumerate as `05c6:9008` (Qualcomm Emergency Download Mode / QHSUSB__BULK).

---

## 2. Full eMMC Raw Dump (Option 2)
To dump the entire 4GB eMMC storage into a single `.bin` file:
```bash
python3 flasher.py
```
Select **Option 2** from the interactive menu. The tool will invoke `edl rf` and create a full backup in the corresponding `backups/<board_id>/` folder.

---

## 3. Full eMMC Restore (Option 3)
To flash a full raw dump back to the dongle:
```bash
python3 flasher.py
```
Select **Option 3**, choose your dump file, and confirm with `y`.

---

## 4. Partition-Level NVRAM Backup (Option 5)
Backs up critical baseband and calibration partitions:
- `fsc`, `fsg`
- `modemst1`, `modemst2` (IMEI & RF Calibration)
- `modem`, `persist`, `sec`
