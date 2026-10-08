# Troubleshooting & FAQ

Below are common issues, root causes, and verified fixes across OpenWrt, Stock Android, and Linux host systems:

---

## 1. OpenWrt Issues

### No Network / Modem Stuck at Searching (Missing Carrier MBN)
If the modem status shows *Searching* or fails to register with cellular towers, the baseband is missing its regional operator configuration (`MCFG_SW.MBN`).

*(Note: In this repository's pre-built firmware for Board JZ0145, `MCFG_SW_ROW.MBN` is already pre-injected into `/lib/firmware/MCFG_SW.MBN`).*

**Manual extraction & fix:**
1. Extract `modem.bin` from your factory firmware dump using 7-Zip or mount it as a FAT16 partition.
2. Locate the appropriate regional profile inside:
   ```text
   IMAGE/MODEM_PR/MCFG/CONFIGS/MCFG_SW/GENERIC/
   ├── APAC    (Asia Pacific)
   ├── CHINA   (China)
   ├── COMMON  (Universal / Fallback)
   ├── EU      (Europe)
   ├── NA      (North America)
   ├── SA      (South America)
   └── SEA     (South East Asia)
   ```
3. Transfer `MCFG_SW.MBN` to the modem filesystem via SSH or SCP:
   ```bash
   scp MCFG_SW.MBN root@192.168.1.1:/lib/firmware/
   ```
4. Reboot the modem or enable it manually:
   ```bash
   mmcli -m 0 -e
   ```

---

### "Connection Refused" / Firewall Masquerade Issue
If devices connected to the OpenWrt router have local IP access but cannot route traffic out to the internet, verify the WAN firewall zone in LuCI (**Network -> Firewall**):

```text
Name             : INTERNET / WAN
Protocol         : Any
Outbound zone    : wan modem
Source address   : any
Destination addr : any
Action           : MASQUERADE (Rewrite to outbound interface IP)
```

---

### Can't Use RNDIS / USB Gadget After Installation
If your computer (especially Windows) fails to recognize the modem's USB Ethernet interface:
- Download and install the [RNDIS Driver](https://github.com/milkv-duo/duo-files/raw/main/common/RNDIS_drivers_20231018.zip).
- In Windows Device Manager, manually update the unrecognized device to **Microsoft USB RNDIS Adapter**.
- Alternatively, OpenWrt v25 provides CDC-NCM out-of-the-box, which requires zero third-party drivers on macOS, Linux, and Windows 11.

---

### Flasher Ending with `DeviceClass - USBError(5, 'Input/Output Error')`
- **100% Normal**: Occurs when the Firehose reset command is executed. The dongle instantly severs the EDL USB endpoint to reboot the SoC into OpenWrt.

---

## 2. Stock Android Issues

### Missing IMEI (`+CME ERROR: 10` / Null IMEI)
If IMEI was lost during stock Android flashing:
1. Connect via ADB:
   ```bash
   adb shell
   ```
2. Write the 15-digit IMEI back to NVRAM:
   ```bash
   modem_at "AT+WRIMEI=YOUR_15_DIGIT_IMEI"
   ```
3. Reboot the device:
   ```bash
   reboot
   ```

---

## 3. Host System & Linux Network Issues

### No Internet via RNDIS / USB Sharing on Linux Host
If host machines fail to route traffic through the dongle's USB network interface (`usb0`):
```bash
nmcli connection modify usb0 ipv4.method shared
nmcli connection down usb0
nmcli connection up usb0
```

