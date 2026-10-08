#!/usr/bin/env python3
"""
MSM8916 Dedicated EDL Backup & Operations Tool
Backs up critical partitions: modemst1, modemst2, fsg, fsc, persist, boot
"""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EDL_SCRIPT = Path("/Volumes/SSD-DATA/Projects/msm8916-4g-dongle-openwrt/edl/edl.py")
LOADER = Path("/Volumes/SSD-DATA/Projects/msm8916-4g-dongle-openwrt/edl/prog_emmc_firehose_8916.mbn")
BACKUP_DIR = BASE_DIR / "backups" / "jz01-45-v33"

CRITICAL_PARTITIONS = ["modemst1", "modemst2", "fsg", "fsc", "persist", "boot"]


def run_edl(cmd: list[str]) -> subprocess.CompletedProcess:
    full_cmd = [
        sys.executable,
        str(EDL_SCRIPT),
        f"--loader={LOADER}",
    ] + cmd
    print(f"\n[EXEC] {' '.join(full_cmd)}")
    return subprocess.run(full_cmd, check=True)


def check_edl_device() -> bool:
    print("\n--- Mengecek Port Qualcomm EDL 9008 ---")
    try:
        res = subprocess.run(
            ["ioreg", "-p", "IOUSB", "-w0", "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        if "QHSUSB__BULK" in res.stdout or "9008" in res.stdout:
            print("[OK] Perangkat Qualcomm EDL 9008 terdeteksi!")
            return True
        else:
            print("[WAIT] Perangkat belum dalam mode EDL 9008.")
            print("Silakan cabut dongle, tahan tombol Reset, lalu colokkan kembali ke USB.")
            return False
    except Exception as e:
        print(f"[ERROR] Gagal membaca USB registry: {e}")
        return False


def backup_partitions() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Memulai Backup Partisi ke: {BACKUP_DIR} ===")

    for part in CRITICAL_PARTITIONS:
        out_file = BACKUP_DIR / f"{part}.bin"
        print(f"\n[*] Dumping partisi: {part} -> {out_file.name}...")
        try:
            run_edl(["r", part, str(out_file)])
            print(f"[OK] Sukses backup {part}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Gagal membaca partisi {part}: {e}")
            sys.exit(1)

    print("\n[SUCCESS] Seluruh partisi EFS & boot berhasil di-backup!")
    print(f"Lokasi: {BACKUP_DIR}")


def main() -> None:
    print("=" * 60)
    print("      MSM8916 JZ01-45 EDL Backup Tool")
    print("=" * 60)

    if not check_edl_device():
        sys.exit(1)

    backup_partitions()


if __name__ == "__main__":
    main()
