#!/usr/bin/env python3
"""
MSM8916 OpenWrt Flasher & R&D Interactive Toolkit
"""

import os
import subprocess
import sys
from pathlib import Path

SUPPORTED_BOARDS = {
    "1": {
        "id": "jz01-45-v33",
        "name": "JZ01-45-v33 (JZxxx Series - Current Focus)",
        "dtb": "msm8916-handsome-jz01-45-v33.dtb",
    },
    "2": {
        "id": "thwc-uf896",
        "name": "THWC-UF896 (UF896 Series)",
        "dtb": "msm8916-thwc-uf896.dtb",
    },
    "3": {
        "id": "thwc-ufi001c",
        "name": "THWC-UFI001C (UFIxxx Series)",
        "dtb": "msm8916-thwc-ufi001c.dtb",
    },
    "4": {
        "id": "fy-mf800",
        "name": "FY-MF800 (MF800 Series)",
        "dtb": "msm8916-fy-mf800.dtb",
    },
}

BASE_DIR = Path(__file__).resolve().parent
FIRMWARE_DIR = BASE_DIR / "firmware"
BACKUP_DIR = BASE_DIR / "backups"
PACKAGES_DIR = BASE_DIR / "packages"


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"\n[EXEC] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def check_fastboot() -> bool:
    print("\n--- Cek Perangkat Fastboot ---")
    try:
        res = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, check=True)
        devices = [line for line in res.stdout.strip().splitlines() if line.strip()]
        if not devices:
            print("[WARN] Tidak ada perangkat dalam mode fastboot terdeteksi.")
            return False
        for dev in devices:
            print(f"[FOUND] {dev}")
        return True
    except FileNotFoundError:
        print("[ERROR] 'fastboot' binary tidak ditemukan di sistem PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] fastboot command gagal: {e}")
        return False


def select_board() -> dict:
    print("\n=== Pilih Board Target ===")
    for key, val in SUPPORTED_BOARDS.items():
        print(f"[{key}] {val['name']}")
    
    choice = input("\nMasukkan nomor board [1]: ").strip() or "1"
    selected = SUPPORTED_BOARDS.get(choice, SUPPORTED_BOARDS["1"])
    print(f"-> Board terpilih: {selected['name']} ({selected['id']})")
    return selected


def flash_openwrt(board_meta: dict) -> None:
    board_id = board_meta["id"]
    boot_img = FIRMWARE_DIR / f"openwrt-{board_id}-boot.img"
    rootfs_img = FIRMWARE_DIR / "openwrt-rootfs.img"

    print(f"\nTarget: {board_meta['name']}")
    print(f"Boot image  : {boot_img} ({'Ditemukan' if boot_img.exists() else 'TIDAK DITEMUKAN'})")
    print(f"Rootfs image: {rootfs_img} ({'Ditemukan' if rootfs_img.exists() else 'TIDAK DITEMUKAN'})")

    if not check_fastboot():
        input("\nTekan Enter untuk kembali ke menu...")
        return

    confirm = input("\nLanjutkan proses flash fastboot? (y/N): ").strip().lower()
    if confirm != "y":
        print("[ABORT] Flash dibatalkan.")
        return

    if not boot_img.exists():
        print(f"[ERROR] Image boot tidak ditemukan di: {boot_img}")
        print("Silakan taruh file boot.img yang sesuai di folder firmware/ terlebih dahulu.")
        input("\nTekan Enter untuk kembali ke menu...")
        return

    try:
        run_cmd(["fastboot", "flash", "boot", str(boot_img)])
        if rootfs_img.exists():
            run_cmd(["fastboot", "flash", "rootfs", str(rootfs_img)])
        else:
            print("[INFO] rootfs image tidak ditemukan di firmware/, hanya flash boot.")
        run_cmd(["fastboot", "reboot"])
        print("\n[SUCCESS] Flashing selesai dan perangkat direboot!")
    except subprocess.CalledProcessError as e:
        print(f"[FAILED] Error saat flashing: {e}")

    input("\nTekan Enter untuk kembali ke menu...")


def backup_efs() -> None:
    print("\n=== Backup EFS Partitions ===")
    out_dir = BACKUP_DIR / "efs"
    out_dir.mkdir(parents=True, exist_ok=True)
    partitions = ["modemst1", "modemst2", "fsg", "fsc"]
    print(f"Target folder: {out_dir}")
    print(f"Partisi      : {', '.join(partitions)}")
    print("[INFO] Backup via EDL/Fastboot command siap.")
    input("\nTekan Enter untuk kembali ke menu...")


def interactive_menu() -> None:
    while True:
        print("\n" + "=" * 50)
        print("    MSM8916 OpenWrt Flasher & R&D Toolkit")
        print("=" * 50)
        print("[1] Cek Perangkat Fastboot")
        print("[2] Flash OpenWrt (Pilih Board - Default: JZ01-45-v33)")
        print("[3] Backup EFS Partisi (modemst1, modemst2, fsg, fsc)")
        print("[4] List File di Folder Firmware & Backups")
        print("[0] Keluar")
        print("-" * 50)

        choice = input("Pilih menu [1-4, 0]: ").strip()

        if choice == "1":
            check_fastboot()
            input("\nTekan Enter untuk kembali ke menu...")
        elif choice == "2":
            board = select_board()
            flash_openwrt(board)
        elif choice == "3":
            backup_efs()
        elif choice == "4":
            print("\n--- Isi Folder Firmware ---")
            for f in FIRMWARE_DIR.iterdir():
                print(f"  {f.name}")
            print("\n--- Isi Folder Backups ---")
            for f in BACKUP_DIR.iterdir():
                print(f"  {f.name}")
            input("\nTekan Enter untuk kembali ke menu...")
        elif choice == "0":
            print("Keluar.")
            sys.exit(0)
        else:
            print("Pilihan tidak valid.")


def main() -> None:
    interactive_menu()


if __name__ == "__main__":
    main()
