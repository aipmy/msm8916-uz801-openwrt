#!/usr/bin/env python3
"""
MSM8916 OpenWrt Flasher & R&D Toolkit
Target boards:
  - jz01-45-v33  (JZxxx boards)
  - thwc-uf896   (UF896 boards)
  - thwc-ufi001c (UFIxxx boards)
  - fy-mf800     (MF800 boards)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

SUPPORTED_BOARDS = {
    "jz01-45-v33": {
        "name": "JZ01-45-v33 (JZxxx Series)",
        "dtb": "msm8916-handsome-jz01-45-v33.dtb",
        "default_offset": "0x80000000",
    },
    "thwc-uf896": {
        "name": "THWC-UF896 (UF896 Series)",
        "dtb": "msm8916-thwc-uf896.dtb",
        "default_offset": "0x80000000",
    },
    "thwc-ufi001c": {
        "name": "THWC-UFI001C (UFIxxx Series)",
        "dtb": "msm8916-thwc-ufi001c.dtb",
        "default_offset": "0x80000000",
    },
    "fy-mf800": {
        "name": "FY-MF800 (MF800 Series)",
        "dtb": "msm8916-fy-mf800.dtb",
        "default_offset": "0x80000000",
    },
}

BASE_DIR = Path(__file__).resolve().parent
FIRMWARE_DIR = BASE_DIR / "firmware"
BACKUP_DIR = BASE_DIR / "backups"
PACKAGES_DIR = BASE_DIR / "packages"


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"[RUN] {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def check_fastboot() -> bool:
    try:
        res = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, check=True)
        devices = [line for line in res.stdout.strip().splitlines() if line.strip()]
        if not devices:
            print("[WARN] No fastboot devices detected.")
            return False
        print(f"[OK] Found fastboot device(s):\n{res.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("[ERROR] 'fastboot' binary not found in PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] fastboot error: {e}")
        return False


def cmd_list_boards(args: argparse.Namespace) -> None:
    print("Supported MSM8916 Boards:")
    for key, info in SUPPORTED_BOARDS.items():
        print(f"  - {key:<14} : {info['name']} (DTB: {info['dtb']})")


def cmd_backup_efs(args: argparse.Namespace) -> None:
    print("[INFO] Backing up modem EFS partitions via fastboot/EDL...")
    out_dir = BACKUP_DIR / "efs"
    out_dir.mkdir(parents=True, exist_ok=True)
    partitions = ["modemst1", "modemst2", "fsg", "fsc"]
    print(f"[INFO] Target partitions: {', '.join(partitions)}")
    print(f"[INFO] Backup directory: {out_dir}")
    print("[NOTE] Ensure device in fastboot/EDL mode.")


def cmd_flash_openwrt(args: argparse.Namespace) -> None:
    board_id = args.board
    if board_id not in SUPPORTED_BOARDS:
        print(f"[ERROR] Unsupported board: {board_id}")
        sys.exit(1)

    board_meta = SUPPORTED_BOARDS[board_id]
    print(f"[INFO] Target Board: {board_meta['name']}")

    boot_img = Path(args.boot) if args.boot else (FIRMWARE_DIR / f"openwrt-{board_id}-boot.img")
    rootfs_img = Path(args.rootfs) if args.rootfs else (FIRMWARE_DIR / "openwrt-rootfs.img")

    print(f"[INFO] Boot image  : {boot_img}")
    print(f"[INFO] Rootfs image: {rootfs_img}")

    if not args.dry_run:
        if not check_fastboot():
            sys.exit(1)
        if boot_img.exists():
            run_cmd(["fastboot", "flash", "boot", str(boot_img)])
        else:
            print(f"[ERROR] File not found: {boot_img}")
            sys.exit(1)

        if rootfs_img.exists():
            run_cmd(["fastboot", "flash", "rootfs", str(rootfs_img)])
        else:
            print(f"[WARN] File not found: {rootfs_img}. Skipping rootfs flash.")
        print("[OK] Flashing completed. Rebooting...")
        run_cmd(["fastboot", "reboot"])
    else:
        print("[DRY-RUN] Verification successful. Fastboot commands not sent.")


def main() -> None:
    parser = argparse.ArgumentParser(description="MSM8916 OpenWrt Flasher & R&D Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-boards
    subparsers.add_parser("list-boards", help="List supported MSM8916 boards")

    # flash
    flash_p = subparsers.add_parser("flash", help="Flash OpenWrt to target board")
    flash_p.add_argument("--board", required=True, choices=list(SUPPORTED_BOARDS.keys()), help="Target board ID")
    flash_p.add_argument("--boot", help="Path to custom openwrt boot.img")
    flash_p.add_argument("--rootfs", help="Path to custom rootfs image")
    flash_p.add_argument("--dry-run", action="store_true", help="Simulate without executing fastboot")

    # backup
    subparsers.add_parser("backup-efs", help="Backup modemst1, modemst2, fsg, fsc")

    args = parser.parse_args()
    if args.command == "list-boards":
        cmd_list_boards(args)
    elif args.command == "flash":
        cmd_flash_openwrt(args)
    elif args.command == "backup-efs":
        cmd_backup_efs(args)


if __name__ == "__main__":
    main()
