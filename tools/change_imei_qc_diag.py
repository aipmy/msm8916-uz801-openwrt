#!/usr/bin/env python3
"""
Qualcomm MSM8916 Direct DIAG NV550 IMEI Writer
Works via USB Qualcomm DIAG Interface (05c6:9091, 05c6:900e, 05c6:9025)
No Android UI / Java framework needed.
"""
import sys
import os
import argparse
import logging
from binascii import unhexlify

# Add edl directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
EDL_PATH = os.path.join(PROJECT_ROOT, "edl")
if not os.path.exists(EDL_PATH):
    EDL_PATH = "/Volumes/SSD-DATA/Projects/msm8916-4g-dongle-openwrt/edl"
sys.path.append(EDL_PATH)

from edlclient.Tools.qc_diag import qcdiag

def encode_imei_nv550(imei_str):
    if len(imei_str) != 15 or not imei_str.isdigit():
        raise ValueError(f"IMEI must be exactly 15 digits (got {len(imei_str)}): {imei_str}")
    data = imei_str[0] + "A"
    for i in range(1, len(imei_str), 2):
        data += imei_str[i + 1]
        data += imei_str[i]
    return unhexlify("08" + data)

def decode_imei_nv550(raw_bytes):
    if len(raw_bytes) < 9 or raw_bytes[0] != 8:
        return "Invalid / Empty"
    raw = raw_bytes[:9]
    digits = [
        str(raw[1] >> 4),
        str(raw[2] & 0x0f), str(raw[2] >> 4),
        str(raw[3] & 0x0f), str(raw[3] >> 4),
        str(raw[4] & 0x0f), str(raw[4] >> 4),
        str(raw[5] & 0x0f), str(raw[5] >> 4),
        str(raw[6] & 0x0f), str(raw[6] >> 4),
        str(raw[7] & 0x0f), str(raw[7] >> 4),
        str(raw[8] & 0x0f), str(raw[8] >> 4)
    ]
    return ''.join(digits)

def main():
    parser = argparse.ArgumentParser(description="MSM8916 Qualcomm DIAG NV550 IMEI Writer")
    parser.add_argument("imei", nargs="?", help="Target 15-digit IMEI to write (if omitted, reads current IMEI)")
    parser.add_argument("--vid", default="0x05c6", help="Qualcomm Vendor ID (default 0x05c6)")
    parser.add_argument("--pid", default="0x9091", help="Qualcomm Product ID (default 0x9091)")
    parser.add_argument("--interface", type=int, default=0, help="DIAG USB Interface index (default 0)")
    parser.add_argument("--spc", default="303030303030", help="Security Password Code (default 000000 -> 303030303030)")
    args = parser.parse_args()

    vid = int(args.vid, 16) if args.vid.startswith("0x") else int(args.vid)
    pid = int(args.pid, 16) if args.pid.startswith("0x") else int(args.pid)

    diag = qcdiag(loglevel=logging.INFO, portconfig=[[vid, pid, args.interface]])
    if not diag.connect():
        print(f"[-] ERROR: Failed to connect to Qualcomm DIAG device (VID={hex(vid)}, PID={hex(pid)}, Interface={args.interface})")
        sys.exit(1)

    print(f"[+] Connected to Qualcomm DIAG (VID={hex(vid)}, PID={hex(pid)}, Intf={args.interface})")
    
    # Send SPC
    spc_res = diag.send_spc(args.spc)
    if spc_res and len(spc_res) > 1 and spc_res[1] == 1:
        print("[+] SPC Accepted (Security Unlocked)")
    else:
        print("[!] Warning: SPC was rejected or unexpected response.")

    # Read current IMEI
    ok, nv = diag.read_nvitem(550)
    if ok:
        print(f"[*] Current IMEI in NVRAM: {decode_imei_nv550(nv.data)} (Raw: {nv.data[:9].hex()})")
    else:
        print("[-] Could not read current NV550")

    if args.imei:
        target_imei = args.imei.strip()
        print(f"[*] Writing target IMEI: {target_imei}...")
        diag.write_imei(target_imei)
        
        # Verify readback
        ok_verify, nv_verify = diag.read_nvitem(550)
        if ok_verify:
            verified_imei = decode_imei_nv550(nv_verify.data)
            print(f"[+] Verified IMEI in NVRAM: {verified_imei} (Raw: {nv_verify.data[:9].hex()})")
            if verified_imei == target_imei:
                print("[+] SUCCESS: IMEI updated and verified in Qualcomm Baseband NVRAM!")
            else:
                print("[-] MISMATCH: Readback IMEI does not match target.")
        else:
            print("[-] ERROR: Failed to verify readback of NV550.")

    diag.disconnect()

if __name__ == "__main__":
    main()
