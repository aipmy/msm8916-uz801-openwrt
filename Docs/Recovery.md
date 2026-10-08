# Recovery Guide

This guide covers emergency recovery steps for Qualcomm MSM8916 dongles in hard-brick or unbootable conditions.

---

## 1. Hardware Pinout & Testpads

If the modem does not turn on, does not enumerate via USB, or stays dark without LED illumination:

### USB Pinout:
```text
  [ 1: VBUS (5V) ]
  [ 2: D- (Data -) ]
  [ 3: D+ (Data +) ]  <--- Short this to GND
  [ 4: GND (Ground) ] <--- Short this to D+
```

### Procedure:
1. Unplug the dongle from your host PC.
2. Short **Pin 3 (D+)** to **Pin 4 (GND)** using a small jumper wire, paperclip, or metallic tweezer.
3. Insert the dongle into your USB port while holding the short.
4. Count 3 seconds, then release the short.
5. Check USB device enumeration:
   - On macOS: `ioreg -p IOUSB -w 0 | grep 9008`
   - On Linux: `lsusb | grep 05c6:9008`
   - On Windows: Device Manager shows `Qualcomm HS-USB QDLoader 9008`.

---

## 2. Emergency Full Storage Unbrick
Once in EDL 9008 mode:
```bash
python3 flasher.py
```
Select **Option 3** (`Restore Full eMMC`) and select the original stock factory dump (`full_dump_*.bin`).
This writes back every sector including partition tables, primary bootloaders (PBL/SBL1), and radio NVRAM.
