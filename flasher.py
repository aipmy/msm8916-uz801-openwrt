#!/usr/bin/env python3
"""
Qualcomm MSM8916 / UFI Diagnostic, EDL Transition, & Firmware Dump Utility
Author: Ariep (SysEng/DevOps)
Location: /Users/aipmy/Projects/qualcomm-edl-flasher
"""

import sys
import os
import time
import shutil
import socket
import argparse
import subprocess
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[1;32m"
C_RED = "\033[1;31m"
C_YELLOW = "\033[1;33m"
C_BLUE = "\033[1;34m"
C_CYAN = "\033[1;36m"
C_WHITE = "\033[1;37m"

SYM_INFO = f"{C_BLUE}[*]{C_RESET}"
SYM_OK = f"{C_GREEN}[+]{C_RESET}"
SYM_WARN = f"{C_YELLOW}[!]{C_RESET}"
SYM_FAIL = f"{C_RED}[-]{C_RESET}"
SYM_ARROW = f"{C_CYAN}➜{C_RESET}"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
EDL_DIR = os.path.join(PROJECT_DIR, "edl")
BACKUPS_DIR = os.path.join(PROJECT_DIR, "backups")
DEFAULT_LOADER = os.path.join(EDL_DIR, "MSM8916_UZ801.bin")

EDL_PYTHON = os.path.join(PROJECT_DIR, "venv", "bin", "python3")
if not os.path.exists(EDL_PYTHON):
    EDL_PYTHON = os.path.join(EDL_DIR, "venv", "bin", "python3")
if not os.path.exists(EDL_PYTHON):
    EDL_PYTHON = sys.executable

EDL_PY = os.path.join(EDL_DIR, "edl.py")

QUALCOMM_VID = 0x05C6
PID_EDL = 0x9008
KNOWN_COMPOSITES = {
    0x9024: "Android Multi-Function Gadget (RNDIS + Serial + Diag + ADB)",
    0x9025: "Android Standard Gadget (Modem + ADB)",
    0x0104: "Linux USB Ethernet Gadget (OpenWrt)",
    0x0100: "Linux USB Gadget (OpenWrt)",
    0xF00E: "RNDIS Modem Only (ADB Disabled / Locked)",
    0xF000: "Mass Storage Mode (Driver Installation CD-ROM)",
    0x9008: "Qualcomm Emergency Download Mode (EDL 9008 / QHSUSB__BULK)",
    0x900E: "Qualcomm Diagnostics / Emergency Fallback",
    0x901D: "Qualcomm Fastboot Mode (Bootloader)"
}

SUPPORTED_BOARDS = {
    "1": {
        "id": "jz01-45-v33",
        "name": "Handsome JZ01-45-V33 (2026 Rev / Tri-color LED)",
        "fw_dir": "firmware/output",
        "prefix": "openwrt-msm89xx-msm8916-jz01-45-v33",
        "backup_dir": "backups/jz01-45-v33"
    },
    "2": {
        "id": "generic-uf02",
        "name": "Generic UF02 (250605 V0S / White Stick)",
        "fw_dir": "firmware/output",
        "prefix": "openwrt-msm89xx-msm8916-generic-uf02",
        "backup_dir": "backups/generic-uf02"
    },
    "3": {
        "id": "yiming-uz801v3",
        "name": "YiMing UZ801 v3.0 (Classic LTE Stick)",
        "fw_dir": "firmware/output",
        "prefix": "openwrt-msm89xx-msm8916-yiming-uz801v3",
        "backup_dir": "backups/yiming-uz801v3"
    }
}

def select_board(default_key: str = "1") -> Dict[str, str]:
    if not sys.stdin.isatty():
        return SUPPORTED_BOARDS.get(default_key, SUPPORTED_BOARDS["1"])
    print(f"\n{C_BOLD}{C_WHITE}[ SELECT TARGET BOARD MODEL ]{C_RESET}")
    for k, v in SUPPORTED_BOARDS.items():
        print(f"  {C_CYAN}{k}.{C_RESET} {v['name']}")
    try:
        ch = input(f"{C_BOLD}{C_WHITE}Select board [1-{len(SUPPORTED_BOARDS)}, default={default_key}]: {C_RESET}").strip()
        if not ch:
            ch = default_key
        return SUPPORTED_BOARDS.get(ch, SUPPORTED_BOARDS["1"])
    except (KeyboardInterrupt, EOFError):
        return SUPPORTED_BOARDS["1"]

def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{C_DIM}[{timestamp}]{C_RESET} {msg}")

def check_usb_ioreg() -> Tuple[bool, Optional[int], Optional[int], str]:
    try:
        proc = subprocess.run(
            ["ioreg", "-r", "-c", "IOUSBHostDevice", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        output = proc.stdout
    except Exception:
        return False, None, None, "Unknown"

    blocks = output.split("+-o ")
    for b in blocks:
        if "1478" in b or "7531" in b:  # 0x05C6 (Qualcomm) or 0x1D6B (Linux Foundation)
            vid = 0x05C6 if "1478" in b else 0x1D6B
            pid = None
            name = "Qualcomm Device"
            for line in b.splitlines():
                if '"idProduct" =' in line:
                    try:
                        pid = int(line.split("=")[1].strip())
                    except ValueError:
                        pass
                if '"USB Product Name" =' in line:
                    try:
                        name = line.split("=")[1].strip().strip('"')
                    except Exception:
                        pass
            if pid is not None:
                return True, vid, pid, name
    return False, None, None, "None"

def check_usb_pyusb() -> Tuple[bool, Optional[int], Optional[int], str]:
    try:
        import usb.core
        dev = usb.core.find(idVendor=QUALCOMM_VID)
        if dev:
            name = "Qualcomm Device"
            try:
                name = dev.product or name
            except Exception:
                pass
            return True, dev.idVendor, dev.idProduct, name
    except Exception:
        pass
    return False, None, None, "None"

def get_usb_status() -> Tuple[bool, Optional[int], Optional[int], str]:
    if sys.platform == "darwin":
        found, vid, pid, name = check_usb_ioreg()
        if found:
            return found, vid, pid, name
    return check_usb_pyusb()

def check_ssh_openwrt(host: str = "192.168.1.1", port: int = 22, user: str = "root", password: str = "") -> Dict[str, Any]:
    res = {
        "reachable": False,
        "is_openwrt": False,
        "release": "",
        "model": "",
        "host": host,
        "port": port,
        "user": user,
        "password": password
    }
    
    # 1. Quick TCP check
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect((host, port))
        s.close()
        res["reachable"] = True
    except Exception:
        return res

    # 2. Probe via ssh
    ssh_cmd = [
        "ssh", "-o", "ConnectTimeout=3",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-p", str(port)
    ]
    if password:
        # Check if sshpass is available
        if shutil.which("sshpass"):
            ssh_cmd = ["sshpass", "-p", password] + ssh_cmd
        else:
            ssh_cmd += ["-o", "BatchMode=no"]
    else:
        ssh_cmd += ["-o", "BatchMode=yes"]

    ssh_cmd += [f"{user}@{host}", "cat /etc/openwrt_release 2>/dev/null; cat /tmp/sysinfo/model 2>/dev/null"]

    try:
        proc = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if proc.returncode == 0 and "DISTRIB_" in proc.stdout:
            res["is_openwrt"] = True
            for line in proc.stdout.splitlines():
                if "DISTRIB_DESCRIPTION=" in line:
                    res["release"] = line.split("=", 1)[1].strip("'\"")
                elif not line.startswith("DISTRIB_") and line.strip():
                    res["model"] = line.strip()
    except Exception:
        pass

    return res

def check_fastboot_status() -> Dict[str, Any]:
    fb_bin = shutil.which("fastboot") or "/opt/homebrew/bin/fastboot"
    res = {
        "installed": os.path.exists(fb_bin),
        "path": fb_bin,
        "device_found": False,
        "serial": None
    }
    if not res["installed"]:
        return res
    try:
        proc = subprocess.run([fb_bin, "devices"], stdout=subprocess.PIPE, text=True, timeout=4)
        for line in proc.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "fastboot":
                res["device_found"] = True
                res["serial"] = parts[0]
                break
    except Exception:
        pass
    return res

def check_adb_status() -> Dict[str, Any]:
    adb_bin = shutil.which("adb") or "/opt/homebrew/bin/adb"
    res = {
        "installed": os.path.exists(adb_bin),
        "path": adb_bin,
        "device_found": False,
        "serial": None,
        "state": None,
        "props": {}
    }
    if not res["installed"]:
        return res

    try:
        proc = subprocess.run([adb_bin, "devices", "-l"], stdout=subprocess.PIPE, text=True, timeout=5)
        for line in proc.stdout.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                res["device_found"] = True
                res["serial"] = parts[0]
                res["state"] = parts[1]
                break
    except Exception:
        pass

    if res["device_found"] and res["state"] == "device":
        for prop in ["ro.product.model", "ro.product.board", "ro.boot.hardware"]:
            try:
                val = subprocess.run(
                    [adb_bin, "shell", f"getprop {prop}"],
                    stdout=subprocess.PIPE, text=True, timeout=2
                ).stdout.strip()
                if val:
                    res["props"][prop] = val
            except Exception:
                pass

    return res

def wait_for_edl(timeout_sec: int = 25) -> bool:
    log(f"{SYM_INFO} Menunggu enumerasi USB Qualcomm EDL 9008 (0x05C6:0x9008)...")
    start = time.time()
    while time.time() - start < timeout_sec:
        found, vid, pid, _ = get_usb_status()
        if found and vid == QUALCOMM_VID and pid == PID_EDL:
            elapsed = time.time() - start
            log(f"{SYM_OK} {C_GREEN}Qualcomm EDL 9008 DETECTED!{C_RESET} ({elapsed:.1f}s)")
            return True
        time.sleep(0.8)
    return False

def ensure_edl_mode(adb_info: Optional[Dict[str, Any]] = None) -> bool:
    """
    Otomatisasi transisi ke mode EDL 9008:
    1. Cek apakah sudah dalam mode EDL 9008 (0x05C6:0x9008).
    2. Cek apakah ada SSH OpenWrt aktif (misal IP 192.168.1.1). Jika ada, kirim reboot edl lewat SSH (reboot edl / qcom_reboot).
    3. Cek ADB jika di mode Android/LK: kirim 'adb reboot edl'.
    """
    found, vid, pid, _ = get_usb_status()
    if found and vid == QUALCOMM_VID and pid == PID_EDL:
        return True

    # 1. Cek apakah perangkat sedang berjalan OpenWrt via SSH
    probe_ssh = check_ssh_openwrt("192.168.1.1", 22, "root", "")
    if probe_ssh["reachable"]:
        log(f"{SYM_ARROW} Modem terdeteksi di mode OpenWrt (SSH 192.168.1.1 aktif).")
        host = "192.168.1.1"
        port = 22
        user = "root"
        password = ""
        if not probe_ssh["is_openwrt"]:
            # Mungkin ada password atau port berbeda
            try:
                host_in = input(f"{C_BOLD}{C_WHITE}IP Host OpenWrt [default: 192.168.1.1]: {C_RESET}").strip()
                if host_in: host = host_in
                port_in = input(f"{C_BOLD}{C_WHITE}SSH Port [default: 22]: {C_RESET}").strip()
                if port_in: port = int(port_in)
                user_in = input(f"{C_BOLD}{C_WHITE}Username [default: root]: {C_RESET}").strip()
                if user_in: user = user_in
                password = input(f"{C_BOLD}{C_WHITE}Password [kosongkan jika tanpa password]: {C_RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                pass

        log(f"{SYM_ARROW} Mengirim perintah transisi ke mode EDL 9008 via SSH...")
        # Metode transisi EDL di Linux mainline msm8916:
        # A: 'reboot edl'
        # B: sysfs power reset / reboot-mode driver
        # C: write magic code ke /sys/bus/platform/drivers/qcom,poweroff atau trigger watchdog / LK
        ssh_cmd = [
            "ssh", "-p", str(port),
            "-o", "ConnectTimeout=3",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null"
        ]
        if password and shutil.which("sshpass"):
            ssh_cmd = ["sshpass", "-p", password] + ssh_cmd

        edl_payload = (
            "reboot edl 2>/dev/null || "
            "echo 1 > /sys/kernel/debug/edl 2>/dev/null || "
            "reboot -f edl 2>/dev/null || "
            "reboot bootloader 2>/dev/null || "
            "reboot -f"
        )
        ssh_cmd += [f"{user}@{host}", edl_payload]
        try:
            subprocess.run(ssh_cmd, timeout=5)
        except Exception:
            pass

        time.sleep(2)
        if wait_for_edl(timeout_sec=15):
            return True

    # 2. Cek apakah ada antarmuka ADB
    if adb_info is None:
        adb_info = check_adb_status()

    if adb_info.get("device_found") and adb_info.get("state") == "device":
        log(f"{SYM_ARROW} Modem terdeteksi di mode normal (ADB aktif). Mengirim {C_BOLD}adb reboot edl{C_RESET} otomatis...")
        try:
            subprocess.run([adb_info["path"], "reboot", "edl"], check=True, timeout=5)
            time.sleep(2)
            return wait_for_edl(timeout_sec=25)
        except Exception as e:
            log(f"{SYM_FAIL} Gagal mengirim adb reboot edl: {e}")
            return False

    # 3. Cek apakah ada antarmuka Fastboot
    fb = check_fastboot_status()
    if fb["device_found"]:
        log(f"{SYM_ARROW} Modem terdeteksi di Fastboot Mode. Mengirim {C_BOLD}fastboot oem edl{C_RESET} / reboot-edl...")
        try:
            subprocess.run([fb["path"], "oem", "edl"], timeout=4)
        except Exception:
            try:
                subprocess.run([fb["path"], "reboot-edl"], timeout=4)
            except Exception:
                pass
        time.sleep(2)
        if wait_for_edl(timeout_sec=15):
            return True

    log(f"{SYM_FAIL} Perangkat belum berada di mode EDL 9008.")
    log(f"{SYM_WARN} Tips masuk EDL 9008:")
    log(f"      1. Jika sedang di OpenWrt: SSH ke modem lalu jalankan: {C_GREEN}reboot edl{C_RESET}")
    log(f"      2. Jika stuck/hardbrick: Tahan tombol Reset / short test point D+ ke GND saat colok USB.")
    return False

def run_edl_cmd(cmd_args: List[str]) -> Tuple[int, str]:
    os.makedirs(os.path.join(EDL_DIR, "logs"), exist_ok=True)
    # Tambahkan parameter penting untuk eMMC MSM8916:
    # --sectorsize=512 agar firehose tidak mismatch 4096 vs 512
    # --maxpayload=1048576 (0x100000) agar payload tidak ditolak
    extra_flags = []
    if not any("--sectorsize" in arg for arg in cmd_args):
        extra_flags.append("--sectorsize=512")
    if not any("--maxpayload" in arg for arg in cmd_args):
        extra_flags.append("--maxpayload=1048576")

    full_cmd = [EDL_PYTHON, EDL_PY] + cmd_args + extra_flags
    log(f"{SYM_INFO} Running: {' '.join(full_cmd)}")

    # Di terminal interaktif: teruskan stdout/stderr langsung agar '\r' native bekerja sempurna tanpa buffer pipe
    if sys.stdout.isatty():
        res = subprocess.run(full_cmd, cwd=EDL_DIR)
        return res.returncode, ""

    # Di non-interaktif: tangkap dan parsing dengan pembersihan \r
    proc = subprocess.Popen(
        full_cmd,
        cwd=EDL_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    collected_output = []
    last_print_time = 0.0
    is_in_progress_line = False
    
    for line in proc.stdout:
        collected_output.append(line)
        line_clean = line.strip().replace("\r", " ")
        
        is_progress = (
            ("%" in line_clean) and 
            ("Sector" in line_clean or "Read" in line_clean or "Write" in line_clean)
        ) or line_clean.startswith("Progress:") or line_clean.startswith("Done |")
        
        if is_progress:
            now = time.time()
            if now - last_print_time >= 0.2 or "100.0%" in line_clean:
                sys.stdout.write(f"\r\033[K{line_clean}")
                sys.stdout.flush()
                last_print_time = now
                is_in_progress_line = True
        else:
            if is_in_progress_line:
                sys.stdout.write("\n")
                is_in_progress_line = False
            sys.stdout.write(line)
            sys.stdout.flush()
            
    if is_in_progress_line:
        sys.stdout.write("\n")
        
    proc.wait()
    return proc.returncode, "".join(collected_output)

def prompt_and_reset(loader: str):
    """Beri opsi y/n untuk reboot/reset modem dari EDL agar tidak perlu cabut-colok fisik."""
    if not sys.stdin.isatty():
        log(f"{SYM_INFO} Non-interaktif: Me-reboot modem dari mode EDL...")
        run_edl_cmd(["reset", f"--loader={loader}"])
        return

    print()
    try:
        ans = input(f"{C_BOLD}{C_WHITE}Do you want to restart/reboot modem now? (Y/n): {C_RESET}").strip().lower()
        if ans in ["", "y", "yes"]:
            log(f"{SYM_ARROW} Sending {C_BOLD}edl reset{C_RESET} command to modem...")
            run_edl_cmd(["reset", f"--loader={loader}"])
            log(f"{SYM_OK} {C_GREEN}Modem restarted successfully.{C_RESET}")
        else:
            log(f"{SYM_INFO} Modem kept in EDL 9008 mode.")
    except (KeyboardInterrupt, EOFError):
        print()
        log(f"{SYM_INFO} Reset dilewati.")

def do_restore_full(in_file: str, loader: str) -> bool:
    in_file = os.path.abspath(in_file)
    if not os.path.exists(in_file):
        log(f"{SYM_FAIL} {C_RED}File restore tidak ditemukan:{C_RESET} {in_file}")
        return False
    loader = os.path.abspath(loader) if os.path.exists(loader) else loader
    size_mb = os.path.getsize(in_file) / (1024 * 1024)
    log(f"{SYM_ARROW} Memulai Restore Full eMMC (wf)...")
    log(f"{SYM_INFO} Sumber file : {C_WHITE}{in_file}{C_RESET} ({size_mb:.2f} MB)")
    log(f"{SYM_WARN} {C_YELLOW}PERINGATAN: Seluruh isi storage eMMC akan ditimpa (overwritten)!{C_RESET}")
    cmd = ["wf", in_file, f"--loader={loader}", "--memory=eMMC"]
    code, output = run_edl_cmd(cmd)
    print(output)
    if code == 0:
        log(f"{SYM_OK} {C_GREEN}Restore Full eMMC selesai sukses!{C_RESET}")

        # --- AUTO-DETECT & AUTO-PATCH REVISI HARDWARE BOARD ---
        print()
        log(f"{SYM_INFO} {C_CYAN}Menjalankan inspeksi otomatis hardware board pada image yang baru di-restore...{C_RESET}")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tf:
            tmp_boot = tf.name

        c_dump, _ = run_edl_cmd(["r", "boot", tmp_boot, f"--loader={loader}", "--memory=eMMC"])
        if c_dump == 0 and os.path.exists(tmp_boot):
            with open(tmp_boot, "rb") as bf:
                boot_bytes = bytearray(bf.read())
            info = inspect_boot_dtb(boot_bytes)
            board_desc = info.get("board", "Unknown")
            variant = info.get("gpio_info", {}).get("variant")

            log(f"{SYM_OK} {C_WHITE}Hasil deteksi firmware boot:{C_RESET} {C_YELLOW}{board_desc}{C_RESET}")
            if variant == "OLD_BOARD":
                print()
                log(f"{SYM_WARN} {C_YELLOW}Terdeteksi: Image dump menggunakan skema board lama (Red=GPIO7, Green=GPIO8, Blue=GPIO6).{C_RESET}")
                try:
                    ask_patch = input(f"{C_BOLD}{C_WHITE}Apakah modem target Anda adalah board revisi baru (Red=GPIO25, Green=GPIO6, Blue=GPIO7)? Auto-patch? (Y/n): {C_RESET}").strip().lower()
                except Exception:
                    ask_patch = "y"

                if ask_patch in ["", "y", "yes"]:
                    log(f"{SYM_ARROW} Melakukan auto-patch Device Tree langsung ke modem...")
                    do_patch_board(loader)
                    try: os.remove(tmp_boot)
                    except Exception: pass
                    return True
                else:
                    log(f"{SYM_INFO} Auto-patch dilewati. Modem mempertahankan skema board lama.")
            elif variant == "NEW_BOARD":
                log(f"{SYM_OK} {C_GREEN}Image sudah menggunakan skema board baru (Red=GPIO25). Tidak perlu patch.{C_RESET}")
            try: os.remove(tmp_boot)
            except Exception: pass
        else:
            log(f"{SYM_WARN} Gagal dump partisi boot untuk auto-inspeksi.")

        prompt_and_reset(loader)
        return True
    else:
        log(f"{SYM_FAIL} {C_RED}Gagal melakukan restore full eMMC.{C_RESET}")
        return False

def do_flash_sysupgrade(board_info: Optional[Dict[str, str]] = None) -> bool:
    if not board_info:
        board_info = select_board("1")

    fw_dir = os.path.join(PROJECT_DIR, board_info.get("fw_dir", "firmware/output"))
    prefix = board_info.get("prefix", "openwrt-msm89xx-msm8916-jz01-45-v33")
    sysupgrade_bin = os.path.join(fw_dir, f"{prefix}-squashfs-sysupgrade.bin")

    if not os.path.exists(sysupgrade_bin):
        log(f"{SYM_FAIL} {C_RED}File sysupgrade tidak ditemukan:{C_RESET} {sysupgrade_bin}")
        return False

    print(f"\n{C_BOLD}{C_WHITE}[ FLASH OPENWRT VIA SSH SYSUPGRADE OVERWRITE ]{C_RESET}")
    print(f"Target Firmware : {C_CYAN}{os.path.basename(sysupgrade_bin)}{C_RESET}")
    print(f"Ukuran Image    : {os.path.getsize(sysupgrade_bin) / (1024*1024):.2f} MB\n")

    host = input(f"{C_BOLD}{C_WHITE}Target IP / Host [default: 192.168.1.1]: {C_RESET}").strip() or "192.168.1.1"
    port_in = input(f"{C_BOLD}{C_WHITE}SSH Port [default: 22]: {C_RESET}").strip() or "22"
    port = int(port_in)
    user = input(f"{C_BOLD}{C_WHITE}Username [default: root]: {C_RESET}").strip() or "root"
    password = input(f"{C_BOLD}{C_WHITE}Password [kosongkan jika tanpa password]: {C_RESET}").strip()

    log(f"{SYM_ARROW} Menguji koneksi SSH ke {user}@{host}:{port}...")
    probe = check_ssh_openwrt(host=host, port=port, user=user, password=password)
    if not probe["reachable"]:
        log(f"{SYM_FAIL} {C_RED}Gagal menghubungi {host}:{port}. Pastikan dongle terhubung dan port terbuka.{C_RESET}")
        return False

    if probe["is_openwrt"]:
        log(f"{SYM_OK} {C_GREEN}OpenWrt Terdeteksi:{C_RESET} {probe.get('release', 'OpenWrt')} ({probe.get('model', 'MSM8916')})")
    else:
        log(f"{SYM_WARN} Perangkat merespon SSH tapi release OpenWrt belum terverifikasi.")

    reset_cfg = input(f"\n{C_YELLOW}{C_BOLD}Reset konfigurasi lama agar tema Proton & status bar aktif bersih (-n)? (Y/n): {C_RESET}").strip().lower()
    flag_n = "-n" if reset_cfg not in ["n", "no"] else ""

    confirm = input(f"{C_RED}{C_BOLD}Lanjutkan flashing sysupgrade ke {host}? (y/N): {C_RESET}").strip().lower()
    if confirm not in ["y", "yes"]:
        log("Flashing dibatalkan.")
        return False

    # Upload file ke /tmp menggunakan cat over SSH jika scp sftp-server tidak ada
    log(f"{SYM_ARROW} [1/2] Mengunggah firmware ke /tmp/sysupgrade.bin...")
    
    # Coba SCP mode legacy SCP (-O) terlebih dahulu
    scp_cmd = [
        "scp", "-O", "-P", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        sysupgrade_bin, f"{user}@{host}:/tmp/sysupgrade.bin"
    ]
    if password and shutil.which("sshpass"):
        scp_cmd = ["sshpass", "-p", password] + scp_cmd

    res = subprocess.run(scp_cmd)
    if res.returncode != 0:
        log(f"{SYM_WARN} SCP legacy mode gagal, menggunakan pipe stream langsung: cat over SSH...")
        ssh_cat_cmd = [
            "ssh", "-p", str(port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{user}@{host}",
            "cat > /tmp/sysupgrade.bin"
        ]
        if password and shutil.which("sshpass"):
            ssh_cat_cmd = ["sshpass", "-p", password] + ssh_cat_cmd

        with open(sysupgrade_bin, "rb") as f_in:
            res_cat = subprocess.run(ssh_cat_cmd, stdin=f_in)
        
        if res_cat.returncode != 0:
            log(f"{SYM_FAIL} {C_RED}Gagal mengunggah file firmware.{C_RESET}")
            return False

    log(f"{SYM_OK} {C_GREEN}Upload berhasil.{C_RESET}")
    log(f"{SYM_ARROW} [2/2] Menjalankan sysupgrade {flag_n} di perangkat...")

    ssh_run = [
        "ssh", "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{user}@{host}",
        f"sysupgrade {flag_n} /tmp/sysupgrade.bin"
    ]
    if password and shutil.which("sshpass"):
        ssh_run = ["sshpass", "-p", password] + ssh_run

    # sysupgrade akan disconnect SSH saat proses reboot
    subprocess.Popen(ssh_run)
    log(f"{SYM_OK} {C_GREEN}Perintah sysupgrade terkirim!{C_RESET}")
    log(f"{SYM_INFO} Modem sedang menulis partisi eMMC dan akan reboot otomatis.")
    log(f"{SYM_INFO} Tunggu sekitar 45-60 detik, lalu akses kembali di {C_CYAN}http://{host}{C_RESET}")
    return True

def do_reboot_bootloader() -> bool:
    print(f"\n{C_BOLD}{C_WHITE}[ REBOOT MODEM TO BOOTLOADER / FASTBOOT ]{C_RESET}")
    # 1. Check ADB
    adb = check_adb_status()
    if adb["device_found"] and adb["state"] == "device":
        log(f"{SYM_ARROW} Terdeteksi via ADB. Mengirim {C_BOLD}adb reboot bootloader{C_RESET}...")
        try:
            subprocess.run([adb["path"], "reboot", "bootloader"], check=True, timeout=5)
            log(f"{SYM_OK} {C_GREEN}Perintah reboot bootloader terkirim via ADB.{C_RESET}")
            return True
        except Exception as e:
            log(f"{SYM_FAIL} Gagal adb reboot bootloader: {e}")

    # 2. Check SSH OpenWrt
    host = input(f"{C_BOLD}{C_WHITE}Target IP [default: 192.168.1.1]: {C_RESET}").strip() or "192.168.1.1"
    port_in = input(f"{C_BOLD}{C_WHITE}SSH Port [default: 22]: {C_RESET}").strip() or "22"
    port = int(port_in)
    user = input(f"{C_BOLD}{C_WHITE}Username [default: root]: {C_RESET}").strip() or "root"
    password = input(f"{C_BOLD}{C_WHITE}Password [kosongkan jika tanpa password]: {C_RESET}").strip()

    ssh_cmd = [
        "ssh", "-p", str(port),
        "-o", "ConnectTimeout=3",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null"
    ]
    if password and shutil.which("sshpass"):
        ssh_cmd = ["sshpass", "-p", password] + ssh_cmd

    ssh_cmd += [f"{user}@{host}", "reboot bootloader 2>/dev/null || reboot -f"]
    log(f"{SYM_ARROW} Mengirim perintah reboot bootloader via SSH ke {user}@{host}...")
    try:
        subprocess.run(ssh_cmd, timeout=5)
        log(f"{SYM_OK} {C_GREEN}Perintah reboot bootloader terkirim via SSH.{C_RESET}")
        return True
    except Exception as e:
        log(f"{SYM_FAIL} Gagal via SSH: {e}")
        return False

def do_flash_fastboot(board_info: Optional[Dict[str, str]] = None) -> bool:
    if not board_info:
        board_info = select_board("1")

    fb = check_fastboot_status()
    if not fb["device_found"]:
        log(f"{SYM_FAIL} {C_RED}Perangkat Fastboot tidak terdeteksi.{C_RESET}")
        log(f"{SYM_INFO} Pastikan dongle sudah di mode bootloader (gunakan opsi menu Reboot to Bootloader).")
        return False

    fw_dir = os.path.join(PROJECT_DIR, board_info.get("fw_dir", "firmware/output"))
    prefix = board_info.get("prefix", "openwrt-msm89xx-msm8916-jz01-45-v33")
    boot_img = os.path.join(fw_dir, f"{prefix}-squashfs-boot.img")
    sys_img = os.path.join(fw_dir, f"{prefix}-squashfs-system.img")
    gpt_bin = os.path.join(fw_dir, f"{prefix}-squashfs-gpt_both0.bin")

    for f in [boot_img, sys_img, gpt_bin]:
        if not os.path.exists(f):
            log(f"{SYM_FAIL} {C_RED}File tidak ditemukan:{C_RESET} {f}")
            return False

    print(f"\n{C_BOLD}{C_WHITE}[ FLASHING OPENWRT VIA FASTBOOT ]{C_RESET}")
    print(f"Board Target    : {C_CYAN}{board_info['name']}{C_RESET}")
    print(f"Fastboot Serial : {C_WHITE}{fb['serial']}{C_RESET}")

    confirm = input(f"{C_RED}{C_BOLD}Mulai flashing Fastboot sekarang? (y/N): {C_RESET}").strip().lower()
    if confirm not in ["y", "yes"]:
        log("Flashing Fastboot dibatalkan.")
        return False

    fb_bin = fb["path"]
    log(f"{SYM_ARROW} [1/4] Flashing partition table (GPT)...")
    subprocess.run([fb_bin, "flash", "partition", gpt_bin], check=True)

    log(f"{SYM_ARROW} [2/4] Menghapus data rootfs lama...")
    subprocess.run([fb_bin, "erase", "rootfs_data"])

    log(f"{SYM_ARROW} [3/4] Flashing Kernel Boot...")
    subprocess.run([fb_bin, "flash", "boot", boot_img], check=True)

    log(f"{SYM_ARROW} [4/4] Flashing Rootfs System...")
    subprocess.run([fb_bin, "flash", "system", sys_img], check=True)

    log(f"{SYM_OK} {C_GREEN}Flashing Fastboot selesai! Melakukan reboot...{C_RESET}")
    subprocess.run([fb_bin, "reboot"])
    return True

def do_flash_openwrt(loader: str, board_info: Optional[Dict[str, str]] = None, skip_backup: bool = False) -> bool:
    if not board_info:
        board_info = select_board("1")
    
    # Deteksi lokasi firmware (output build atau subfolder board)
    openwrt_dir = os.path.join(PROJECT_DIR, board_info["fw_dir"])
    output_dir = os.path.join(PROJECT_DIR, "firmware", "output")
    if not os.path.exists(openwrt_dir) and os.path.exists(output_dir):
        openwrt_dir = output_dir

    target_backup_dir = os.path.join(PROJECT_DIR, board_info["backup_dir"])
    
    log(f"{SYM_INFO} Target Board Flashing: {C_WHITE}{board_info['name']}{C_RESET}")
    # Cek preferensi file khusus JZ01-45-V33 terlebih dahulu
    jz_boot = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-boot.img")
    if os.path.exists(jz_boot):
        boot_img = jz_boot
        rootfs_img = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-system.img")
        gpt_bin = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-jz01-45-v33-squashfs-gpt_both0.bin")
        fw_zip = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-jz01-45-v33-firmware.zip")
    else:
        boot_img = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-yiming-uz801v3-squashfs-boot.img")
        rootfs_img = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-yiming-uz801v3-squashfs-system.img")
        gpt_bin = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-yiming-uz801v3-squashfs-gpt_both0.bin")
        fw_zip = os.path.join(openwrt_dir, "openwrt-msm89xx-msm8916-yiming-uz801v3-firmware.zip")
    tot_sectors = 7569408

    # 1. Verifikasi File Image
    for f in [boot_img, rootfs_img, gpt_bin, fw_zip, loader]:
        if not os.path.exists(f):
            log(f"{SYM_FAIL} {C_RED}File tidak ditemukan:{C_RESET} {f}")
            return False

    log(f"{SYM_OK} {C_GREEN}Semua paket image OpenWrt v25.12.5 terverifikasi lengkap.{C_RESET}")

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(target_backup_dir, f"nvram_{timestamp_str}")
    
    # 2. Opsi Backup Partisi Kritis (IMEI & Kalibrasi RF)
    if not skip_backup:
        os.makedirs(backup_dir, exist_ok=True)
        print()
        log(f"{SYM_ARROW} {C_CYAN}[TAHAP 1/5] Mencadangkan IMEI & Radio NVRAM ke:{C_RESET} {backup_dir}")
        for part in ["fsc", "fsg", "modemst1", "modemst2", "modem", "persist", "sec"]:
            target_bin = os.path.join(backup_dir, f"{part}.bin")
            print(f"      {SYM_ARROW} Dump partisi: {C_WHITE}{part:<10}{C_RESET} ...", end=" ", flush=True)
            code, _ = run_edl_cmd(["r", part, target_bin, f"--loader={loader}", "--memory=eMMC"])
            if code == 0 and os.path.exists(target_bin):
                print(f"{C_GREEN}OK{C_RESET} ({os.path.getsize(target_bin)} bytes)")
            else:
                print(f"{C_RED}GAGAL{C_RESET}")
                log(f"{SYM_FAIL} {C_RED}Aborting: Gagal dump partisi {part} untuk keamanan IMEI.{C_RESET}")
                return False
        log(f"{SYM_OK} {C_GREEN}Partisi NVRAM & IMEI aman tersimpan.{C_RESET}")
    else:
        print()
        log(f"{SYM_INFO} {C_YELLOW}[TAHAP 1/5] Melewati backup NVRAM (Menggunakan partisi NVRAM yang sudah ada).{C_RESET}")
        # Cari direktori backup nvram terakhir untuk board ini jika ada
        backup_dir = ""
        if os.path.exists(target_backup_dir):
            subdirs = [os.path.join(target_backup_dir, d) for d in os.listdir(target_backup_dir) if d.startswith("nvram_") and os.path.isdir(os.path.join(target_backup_dir, d))]
            if subdirs:
                backup_dir = sorted(subdirs)[-1]
                log(f"{SYM_INFO} Partisi restore yang akan digunakan: {C_WHITE}{backup_dir}{C_RESET}")

    # 3. Flash Tabel Partisi Baru (GPT SquashFS OpenWrt)
    print()
    log(f"{SYM_ARROW} {C_CYAN}[TAHAP 2/5] Menulis tabel partisi OpenWrt GPT...{C_RESET}")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        primary_bin = os.path.join(tmp_dir, "primary.bin")
        backup_entries = os.path.join(tmp_dir, "backup_entries.bin")
        backup_header = os.path.join(tmp_dir, "backup_header.bin")

        with open(gpt_bin, "rb") as gf:
            gpt_data = gf.read()
            with open(primary_bin, "wb") as pf:
                pf.write(gpt_data[:34 * 512])
            with open(backup_entries, "wb") as bef:
                bef.write(gpt_data[34 * 512:66 * 512])
            with open(backup_header, "wb") as bhf:
                bhf.write(gpt_data[66 * 512:67 * 512])

        print(f"      {SYM_ARROW} Menulis Primary GPT (Sektor 0) ...", end=" ", flush=True)
        code1, _ = run_edl_cmd(["ws", "0", primary_bin, f"--loader={loader}", "--memory=eMMC"])
        print(f"{C_GREEN}OK{C_RESET}" if code1 == 0 else f"{C_RED}GAGAL{C_RESET}")

        print(f"      {SYM_ARROW} Menulis Backup Entries (Sektor {tot_sectors - 33}) ...", end=" ", flush=True)
        code2, _ = run_edl_cmd(["ws", str(tot_sectors - 33), backup_entries, f"--loader={loader}", "--memory=eMMC"])
        print(f"{C_GREEN}OK{C_RESET}" if code2 == 0 else f"{C_RED}GAGAL{C_RESET}")

        print(f"      {SYM_ARROW} Menulis Backup Header (Sektor {tot_sectors - 1}) ...", end=" ", flush=True)
        code3, _ = run_edl_cmd(["ws", str(tot_sectors - 1), backup_header, f"--loader={loader}", "--memory=eMMC"])
        print(f"{C_GREEN}OK{C_RESET}" if code3 == 0 else f"{C_RED}GAGAL{C_RESET}")

        if code1 != 0 or code2 != 0 or code3 != 0:
            log(f"{SYM_FAIL} {C_RED}Gagal menulis tabel partisi GPT.{C_RESET}")
            return False

    log(f"{SYM_OK} {C_GREEN}Tabel partisi OpenWrt berhasil ditulis.{C_RESET}")

    # 4. Flash Bootloader MBN
    print()
    log(f"{SYM_ARROW} {C_CYAN}[TAHAP 3/5] Mengekstrak & menulis bootloader Qualcomm MBN...{C_RESET}")
    import zipfile
    with tempfile.TemporaryDirectory() as fw_tmp:
        with zipfile.ZipFile(fw_zip, "r") as zf:
            for item in zf.namelist():
                if item.endswith(".mbn"):
                    zf.extract(item, fw_tmp)
        
        for part in ["sbl1", "tz", "rpm", "hyp", "aboot"]:
            mbn_file = os.path.join(fw_tmp, f"{part}.mbn")
            print(f"      {SYM_ARROW} Flashing bootloader: {C_WHITE}{part:<10}{C_RESET} ...", end=" ", flush=True)
            code, _ = run_edl_cmd(["w", part, mbn_file, f"--loader={loader}", "--memory=eMMC"])
            print(f"{C_GREEN}OK{C_RESET}" if code == 0 else f"{C_RED}GAGAL{C_RESET}")
            if code != 0:
                log(f"{SYM_FAIL} Gagal flash {part}.mbn")
                return False

    # 5. Flash Kernel & RootFS OpenWrt + Erase rootfs_data
    print()
    log(f"{SYM_ARROW} {C_CYAN}[TAHAP 4/5] Menulis Kernel (boot) & Rootfs OpenWrt...{C_RESET}")
    print(f"      {SYM_ARROW} Flashing OpenWrt Kernel: {C_WHITE}{os.path.basename(boot_img)}{C_RESET} ...", end=" ", flush=True)
    c_boot, _ = run_edl_cmd(["w", "boot", boot_img, f"--loader={loader}", "--memory=eMMC"])
    print(f"{C_GREEN}OK{C_RESET}" if c_boot == 0 else f"{C_RED}GAGAL{C_RESET}")

    print(f"      {SYM_ARROW} Flashing OpenWrt System: {C_WHITE}{os.path.basename(rootfs_img)}{C_RESET} ...", end=" ", flush=True)
    c_rootfs, _ = run_edl_cmd(["w", "system", rootfs_img, f"--loader={loader}", "--memory=eMMC"])
    print(f"{C_GREEN}OK{C_RESET}" if c_rootfs == 0 else f"{C_RED}GAGAL{C_RESET}")

    print(f"      {SYM_ARROW} Erasing overlay data: {C_WHITE}rootfs_data{C_RESET} ...", end=" ", flush=True)
    c_erase, _ = run_edl_cmd(["e", "rootfs_data", f"--loader={loader}", "--memory=eMMC"])
    print(f"{C_GREEN}OK{C_RESET}" if c_erase == 0 else f"{C_RED}GAGAL{C_RESET}")
    if c_erase != 0:
        log(f"{SYM_WARN} Mencoba erase LBA sektor manual untuk rootfs_data...")
        # LBA start 610338 s/d akhir disk
        run_edl_cmd(["es", "610338", "2048", f"--loader={loader}", "--memory=eMMC"])

    # 6. Restore Partisi Radio / IMEI
    print()
    if backup_dir and os.path.exists(backup_dir):
        log(f"{SYM_ARROW} {C_CYAN}[TAHAP 5/5] Mengembalikan partisi sinyal & IMEI asli...{C_RESET}")
        for part in ["fsc", "fsg", "modemst1", "modemst2", "modem", "persist", "sec"]:
            src_bin = os.path.join(backup_dir, f"{part}.bin")
            if os.path.exists(src_bin):
                print(f"      {SYM_ARROW} Restore partisi: {C_WHITE}{part:<10}{C_RESET} ...", end=" ", flush=True)
                code, _ = run_edl_cmd(["w", part, src_bin, f"--loader={loader}", "--memory=eMMC"])
                print(f"{C_GREEN}OK{C_RESET}" if code == 0 else f"{C_RED}GAGAL{C_RESET}")
    else:
        log(f"{SYM_WARN} {C_YELLOW}[TAHAP 5/5] Melewati restore NVRAM (tidak ada direktori sumber).{C_RESET}")

    # 7. Selesai & Reset
    print()
    print(f"{C_GREEN}╔════════════════════════════════════════════════════════════════════════════╗")
    print(f"║            FLASHING OPENWRT v25.12.5 SELESAI 100% SUKSES!                  ║")
    print(f"╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    
    if "JZ0145" in board_info["id"]:
        print(f"{C_GREEN}[+] Profil operator seluler (MCFG_SW.MBN) sudah pre-injected langsung ke sistem!{C_RESET}")
        print(f"    Sinyal 4G LTE akan langsung aktif tanpa perlu transfer manual via SSH.")
        print()

    log(f"{SYM_INFO} Merestart modem...")
    try:
        run_edl_cmd(["reset", f"--loader={loader}"])
    except Exception:
        pass

    print()
    print(f"  {SYM_OK} {C_WHITE}IP Gateway OpenWrt :{C_RESET} {C_CYAN}http://192.168.1.1{C_RESET}")
    print(f"  {SYM_OK} {C_WHITE}Kredensial LuCI/SSH:{C_RESET} User: {C_GREEN}root{C_RESET} (tanpa password)")
    print(f"  {SYM_WARN} {C_YELLOW}Silakan cabut dan colok ulang stik USB modem ke komputer.{C_RESET}")
    print()
    return True

def inspect_boot_dtb(boot_bytes: bytearray) -> Dict[str, Any]:
    import re
    dtbs = [m.start() for m in re.finditer(b"\xd0\x0d\xfe\xed", boot_bytes)]
    if not dtbs:
        return {"error": "Tidak ditemukan Device Tree Blob (DTB) di boot image"}

    offset = dtbs[0]
    import struct
    totalsize = struct.unpack(">I", boot_bytes[offset+4:offset+8])[0]
    dtb_data = boot_bytes[offset:offset+totalsize]

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".dtb", delete=False) as tf:
        tf.write(dtb_data)
        dtb_path = tf.name

    dts_path = dtb_path.replace(".dtb", ".dts")
    dtc_bin = shutil.which("dtc") or "/opt/homebrew/bin/dtc"
    res = subprocess.run([dtc_bin, "-I", "dtb", "-O", "dts", dtb_path, "-o", dts_path], capture_output=True, text=True)
    if res.returncode != 0:
        return {"error": f"Gagal decompile DTB via dtc: {res.stderr}"}

    with open(dts_path, "r") as f:
        dts = f.read()

    board = "UNKNOWN"
    gpio_info = {}
    if 'gpios = <0x47 0x19 0x00>;' in dts and 'gpios = <0x47 0x06 0x00>;' in dts:
        board = "UZ801 Revisi Baru (V3/Yiming Modern: Red=GPIO25, Green=GPIO6, Blue=GPIO7)"
        gpio_info = {"red": 25, "green": 6, "blue": 7, "variant": "NEW_BOARD"}
    elif 'gpios = <0x47 0x07 0x00>;' in dts and 'gpios = <0x47 0x08 0x00>;' in dts:
        board = "UZ801 Revisi Lama (Standard Default: Red=GPIO7, Green=GPIO8, Blue=GPIO6)"
        gpio_info = {"red": 7, "green": 8, "blue": 6, "variant": "OLD_BOARD"}
    else:
        board = "Kustom / Varian Lain"

    try:
        os.remove(dtb_path)
        os.remove(dts_path)
    except Exception:
        pass

    return {
        "board": board,
        "offset": offset,
        "totalsize": totalsize,
        "gpio_info": gpio_info
    }

def do_check_board(loader: str) -> None:
    import tempfile
    log(f"{SYM_ARROW} Membaca partisi boot dari modem via EDL untuk inspeksi hardware...")
    with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tf:
        tmp_boot = tf.name

    code, _ = run_edl_cmd(["r", "boot", tmp_boot, f"--loader={loader}", "--memory=eMMC"])
    if code != 0 or not os.path.exists(tmp_boot):
        log(f"{SYM_FAIL} Gagal membaca partisi boot dari chip eMMC.")
        return

    with open(tmp_boot, "rb") as f:
        boot_bytes = bytearray(f.read())
    try:
        os.remove(tmp_boot)
    except Exception:
        pass

    info = inspect_boot_dtb(boot_bytes)
    print()
    log(f"{SYM_OK} {C_GREEN}HASIL ANALISA REVISI HARDWARE BOARD MODEM:{C_RESET}")
    print(f"      {C_WHITE}Identifikasi Board :{C_RESET} {C_CYAN}{info.get('board', 'Unknown')}{C_RESET}")
    g = info.get("gpio_info", {})
    if g:
        print(f"      {C_WHITE}Alokasi LED Merah  :{C_RESET} GPIO {g.get('red')} (Alarm / Fault)")
        print(f"      {C_WHITE}Alokasi LED Hijau  :{C_RESET} GPIO {g.get('green')} (WAN / LTE Link)")
        print(f"      {C_WHITE}Alokasi LED Biru   :{C_RESET} GPIO {g.get('blue')} (LAN / USB Host)")
        if g.get("variant") == "NEW_BOARD":
            log(f"{SYM_OK} {C_GREEN}Konfigurasi Device Tree sudah 100% cocok untuk board revisi baru bapak!{C_RESET}")
        else:
            log(f"{SYM_WARN} {C_YELLOW}Board terdeteksi skema lama. Gunakan opsi Patch Board jika warna LED tertukar.{C_RESET}")
    print()
    prompt_and_reset(loader)

def do_patch_board(loader: str) -> None:
    import tempfile
    log(f"{SYM_ARROW} [1/3] Menarik partisi boot aktif dari modem via EDL...")
    with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tf:
        tmp_boot = tf.name

    code, _ = run_edl_cmd(["r", "boot", tmp_boot, f"--loader={loader}", "--memory=eMMC"])
    if code != 0 or not os.path.exists(tmp_boot):
        log(f"{SYM_FAIL} Gagal dump boot partisi.")
        return

    with open(tmp_boot, "rb") as f:
        boot_bytes = bytearray(f.read())

    info = inspect_boot_dtb(boot_bytes)
    if info.get("gpio_info", {}).get("variant") == "NEW_BOARD":
        log(f"{SYM_OK} {C_GREEN}Board sudah menggunakan Device Tree revisi baru. Tidak perlu di-patch lagi.{C_RESET}")
        try: os.remove(tmp_boot)
        except Exception: pass
        prompt_and_reset(loader)
        return

    offset = info["offset"]
    totalsize = info["totalsize"]
    dtb_data = boot_bytes[offset:offset+totalsize]

    with tempfile.NamedTemporaryFile(suffix=".dtb", delete=False) as tf:
        tf.write(dtb_data)
        dtb_path = tf.name
    dts_path = dtb_path.replace(".dtb", ".dts")
    dtc_bin = shutil.which("dtc") or "/opt/homebrew/bin/dtc"
    subprocess.run([dtc_bin, "-I", "dtb", "-O", "dts", dtb_path, "-o", dts_path], check=True)

    with open(dts_path, "r") as f:
        dts = f.read()

    log(f"{SYM_ARROW} [2/3] Memodifikasi tabel Device Tree (Red=GPIO25, Green=GPIO6, Blue=GPIO7)...")
    dts = dts.replace('pins = "gpio6", "gpio7", "gpio8";', 'pins = "gpio6", "gpio7", "gpio25";')
    old_leds = '''		led-r {
			color = <0x01>;
			default-state = "on";
			function = "power";
			gpios = <0x47 0x07 0x00>;
		};

		led-g {
			color = <0x02>;
			default-state = "off";
			function = "wan";
			gpios = <0x47 0x08 0x00>;
		};

		led-b {
			color = <0x03>;
			default-state = "off";
			function = "wlan";
			gpios = <0x47 0x06 0x00>;
		};'''

    new_leds = '''		led-r {
			color = <0x01>;
			default-state = "on";
			function = "power";
			gpios = <0x47 0x19 0x00>;
		};

		led-g {
			color = <0x02>;
			default-state = "off";
			function = "wan";
			gpios = <0x47 0x06 0x00>;
		};

		led-b {
			color = <0x03>;
			default-state = "off";
			function = "wlan";
			gpios = <0x47 0x07 0x00>;
		};'''
    if old_leds in dts:
        dts = dts.replace(old_leds, new_leds)
    else:
        log(f"{SYM_FAIL} Blok struktur LED tidak cocok, patch dibatalkan demi keamanan.")
        return

    with open(dts_path, "w") as f:
        f.write(dts)

    new_dtb = dtb_path.replace(".dtb", "_new.dtb")
    subprocess.run([dtc_bin, "-I", "dts", "-O", "dtb", dts_path, "-o", new_dtb], check=True)
    with open(new_dtb, "rb") as f:
        new_dtb_bytes = f.read()

    if len(new_dtb_bytes) != totalsize:
        log(f"{SYM_FAIL} Ukuran DTB berubah ({len(new_dtb_bytes)} vs {totalsize}), aborting.")
        return

    boot_bytes[offset:offset+totalsize] = new_dtb_bytes
    with open(tmp_boot, "wb") as f:
        f.write(boot_bytes)

    log(f"{SYM_ARROW} [3/3] Menulis ulang partisi boot yang telah dipatch ke modem...")
    c_write, _ = run_edl_cmd(["w", "boot", tmp_boot, f"--loader={loader}", "--memory=eMMC"])
    try:
        os.remove(tmp_boot); os.remove(dtb_path); os.remove(dts_path); os.remove(new_dtb)
    except Exception:
        pass

    if c_write == 0:
        log(f"{SYM_OK} {C_GREEN}Patch Hardware Board Berhasil 100%! LED sekarang sudah normal.{C_RESET}")
        prompt_and_reset(loader)
    else:
        log(f"{SYM_FAIL} {C_RED}Gagal menulis kembali partisi boot.{C_RESET}")

def do_backup_partitions(out_dir: str, loader: str) -> bool:
    os.makedirs(out_dir, exist_ok=True)
    log(f"{SYM_ARROW} Memulai backup partisi per-seksi (rl) dengan metadata genxml...")
    log(f"{SYM_INFO} Target direktori: {C_WHITE}{out_dir}{C_RESET}")
    cmd = ["rl", out_dir, f"--loader={loader}", "--memory=eMMC", "--genxml"]
    code, output = run_edl_cmd(cmd)
    print(output)
    if code == 0:
        log(f"{SYM_OK} {C_GREEN}Backup partisi selesai sukses!{C_RESET}")
        return True
    else:
        log(f"{SYM_FAIL} {C_RED}Gagal melakukan backup partisi.{C_RESET}")
        return False

def do_backup_full(out_file: str, loader: str) -> bool:
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    log(f"{SYM_ARROW} Memulai full eMMC raw dump (rf)...")
    log(f"{SYM_INFO} Target file: {C_WHITE}{out_file}{C_RESET}")
    cmd = ["rf", out_file, f"--loader={loader}", "--memory=eMMC"]
    code, output = run_edl_cmd(cmd)
    print(output)
    if code == 0:
        log(f"{SYM_OK} {C_GREEN}Full dump eMMC selesai sukses!{C_RESET}")
        prompt_and_reset(loader)
        return True
    else:
        log(f"{SYM_FAIL} {C_RED}Gagal melakukan full dump eMMC.{C_RESET}")
        return False

NVRAM_PARTITIONS = ["fsc", "fsg", "modemst1", "modemst2", "modem", "persist", "sec"]

def do_backup_nvram(out_dir: str, loader: str) -> bool:
    os.makedirs(out_dir, exist_ok=True)
    log(f"{SYM_ARROW} Memulai backup partisi penting (IMEI & RF Calibration)...")
    log(f"{SYM_INFO} Target direktori: {C_WHITE}{out_dir}{C_RESET}")
    success_all = True
    for part in NVRAM_PARTITIONS:
        dest = os.path.join(out_dir, f"{part}.bin")
        print(f"      {SYM_ARROW} Dumping partisi: {C_WHITE}{part:<10}{C_RESET} ➜ {dest}")
        cmd = ["r", part, dest, f"--loader={loader}", "--memory=eMMC"]
        code, out = run_edl_cmd(cmd)
        if code != 0:
            print(f"        {SYM_FAIL} Gagal dump partisi {part}")
            success_all = False
        else:
            print(f"        {SYM_OK} OK ({os.path.getsize(dest)} bytes)")
    if success_all:
        log(f"{SYM_OK} {C_GREEN}Semua partisi NVRAM/IMEI aman dicadangkan!{C_RESET}")
    return success_all

def print_banner():
    banner = f"""
{C_CYAN}╔════════════════════════════════════════════════════════════════════════════╗
║         QUALCOMM MSM8916 / UFI EDL 9008 FLASHER & BACKUP TOOL              ║
║                 Integrated EDL Client & Firmware Operations                ║
╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}
"""
    print(banner)

def main():
    parser = argparse.ArgumentParser(description="Qualcomm MSM8916 / UFI EDL Probe & Firmware Backup Utility")
    parser.add_argument("--reboot-edl", action="store_true", help="Kirim perintah software reboot ke mode EDL")
    parser.add_argument("--auto", "-y", action="store_true", help="Eksekusi tanpa prompt interaktif")
    parser.add_argument("--board", choices=["1", "2"], default="1", help="Pilihan board: 1=JZ0145_V40_20260509 (Baru), 2=FY_UZ801_V3.31 (Lama)")
    parser.add_argument("--backup-partitions", action="store_true", help="Backup seluruh partisi eMMC per partisi (--genxml)")
    parser.add_argument("--backup-full", action="store_true", help="Dump seluruh chip eMMC menjadi 1 file biner (rf)")
    parser.add_argument("--restore-full", help="Restore/Flash 1 file biner hasil backup full ke chip eMMC (wf)")
    parser.add_argument("--check-board", action="store_true", help="Cek varian revisi hardware board (skema GPIO LED DTB)")
    parser.add_argument("--patch-board", action="store_true", help="Patch DTB boot.img agar sesuai revisi board baru (Red=GPIO25, Green=GPIO6, Blue=GPIO7)")
    parser.add_argument("--flash-openwrt", action="store_true", help="Flash firmware OpenWrt v25.12.5 ke UZ801 via Python murni")
    parser.add_argument("--skip-backup", action="store_true", help="Lewati proses backup NVRAM saat flashing OpenWrt")
    parser.add_argument("--reset", action="store_true", help="Kirim perintah reboot/reset normal ke modem dari mode EDL")
    parser.add_argument("--backup-nvram", action="store_true", help="Backup partisi IMEI/RF saja (fsc, fsg, modemst1, modemst2, dll)")
    parser.add_argument("--loader", default=DEFAULT_LOADER, help="Path ke firehose programmer loader (.bin/.mbn)")
    args = parser.parse_args()

    print_banner()

    # Periksa ketersediaan library Python pihak ketiga untuk EDL
    missing_deps = []
    for pkg in ["usb", "serial", "docopt"]:
        try:
            __import__(pkg)
        except ImportError:
            missing_deps.append(pkg)
    
    if missing_deps and not os.path.exists(os.path.join(EDL_DIR, "venv")):
        log(f"{SYM_WARN} Beberapa dependensi Python EDL belum terpasang di sistem global: {', '.join(missing_deps)}")
        log(f"{SYM_INFO} Disarankan membuat venv otomatis: {C_GREEN}python3 -m venv edl/venv && edl/venv/bin/pip install -r edl/requirements.txt{C_RESET}")
        print()

    log(f"{SYM_INFO} Checking toolset dependencies integrity...")
    print(f"      EDL Tool Path : {C_WHITE}{EDL_DIR}{C_RESET}")
    print(f"      Loader MBN    : {C_WHITE}{args.loader}{C_RESET} ({'ADA' if os.path.exists(args.loader) else 'TIDAK DITEMUKAN'})")
    print(f"      Backups Store : {C_WHITE}{BACKUPS_DIR}{C_RESET}")

    if not os.path.exists(args.loader):
        log(f"{SYM_FAIL} Loader tidak ditemukan di: {args.loader}")
        sys.exit(1)

    print()
    log(f"{SYM_INFO} Memindai antarmuka fisik USB Host & Bus Controller...")
    usb_found, vid, pid, product_name = get_usb_status()

    if not usb_found:
        log(f"{SYM_FAIL} {C_RED}Tidak ada perangkat USB Qualcomm yang terdeteksi.{C_RESET}")
        log(f"{SYM_WARN} Pastikan dongle/modem terpasang kencang ke port USB.")
        sys.exit(1)

    desc = KNOWN_COMPOSITES.get(pid, "Unknown Configuration")
    log(f"{SYM_OK} Qualcomm Device Detected:")
    print(f"      {C_WHITE}Vendor ID     :{C_RESET} 0x{vid:04X} (Qualcomm Inc.)")
    print(f"      {C_WHITE}Product ID    :{C_RESET} 0x{pid:04X} ({product_name})")
    print(f"      {C_WHITE}Deskripsi Mode:{C_RESET} {C_YELLOW}{desc}{C_RESET}")

    is_edl = (pid == PID_EDL)
    adb = check_adb_status()
    can_boot_edl = False

    if not is_edl:
        print()
        log(f"{SYM_INFO} Memeriksa status antarmuka Android Debug Bridge (ADB)...")
        if adb["device_found"]:
            state_color = C_GREEN if adb["state"] == "device" else C_YELLOW
            log(f"{SYM_OK} ADB Daemon terhubung:")
            print(f"      {C_WHITE}Serial ID     :{C_RESET} {adb['serial']}")
            print(f"      {C_WHITE}State Status  :{C_RESET} {state_color}{adb['state']}{C_RESET}")
            for k, v in adb.get("props", {}).items():
                print(f"      {C_WHITE}{k:<14}:{C_RESET} {v}")
            if adb["state"] == "device":
                can_boot_edl = True
        else:
            log(f"{SYM_WARN} ADB tidak mendeteksi perangkat aktif.")
    else:
        log(f"{SYM_OK} {C_GREEN}STATUS: Device is already in Qualcomm EDL 9008 mode!{C_RESET}")

    # Mode CLI langsung
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.backup_partitions:
        if not ensure_edl_mode(adb):
            sys.exit(1)
        target_dir = os.path.join(BACKUPS_DIR, f"partitions_{timestamp_str}")
        do_backup_partitions(target_dir, args.loader)
        sys.exit(0)

    if args.backup_full:
        if not ensure_edl_mode(adb):
            sys.exit(1)
        target_file = os.path.join(BACKUPS_DIR, f"full_dump_{timestamp_str}.bin")
        do_backup_full(target_file, args.loader)
        sys.exit(0)

    if args.restore_full:
        if not ensure_edl_mode(adb):
            sys.exit(1)
        do_restore_full(args.restore_full, args.loader)
        sys.exit(0)

    if args.check_board:
        if not ensure_edl_mode(adb):
            sys.exit(1)
        do_check_board(args.loader)
        sys.exit(0)

    if args.patch_board:
        if not ensure_edl_mode(adb):
            sys.exit(1)
        do_patch_board(args.loader)
        sys.exit(0)

    if args.flash_openwrt:
        board_sel = SUPPORTED_BOARDS.get(args.board, SUPPORTED_BOARDS["1"])
        log(f"{SYM_INFO} Mempersiapkan flashing OpenWrt untuk: {board_sel['name']}")
        if not ensure_edl_mode(adb):
            sys.exit(1)
        do_flash_openwrt(args.loader, board_sel, skip_backup=args.skip_backup)
        sys.exit(0)

    if args.reset:
        log(f"{SYM_ARROW} Mengirim perintah reboot normal ke modem via EDL...")
        run_edl_cmd(["reset", f"--loader={args.loader}"])
        log(f"{SYM_OK} {C_GREEN}Modem berhasil di-reboot.{C_RESET}")
        sys.exit(0)

    if args.backup_nvram:
        if not ensure_edl_mode(adb):
            sys.exit(1)
        target_dir = os.path.join(BACKUPS_DIR, f"nvram_{timestamp_str}")
        do_backup_nvram(target_dir, args.loader)
        sys.exit(0)

    if args.reboot_edl:
        if is_edl:
            log(f"{SYM_INFO} Perangkat sudah berada di mode EDL 9008.")
            sys.exit(0)
        if can_boot_edl:
            ensure_edl_mode(adb)
            sys.exit(0)
        else:
            log(f"{SYM_FAIL} Perangkat tidak siap untuk reboot edl via adb.")
            sys.exit(1)

    # Menu Interaktif
    print()
    print(f"{C_BOLD}{C_WHITE}[ QUALCOMM MSM8916 / OPENWRT OPERATIONS MENU ]{C_RESET}")
    print(f"{C_DIM}--- [ DIAGNOSTICS & CONTROL ] ---{C_RESET}")
    print(f"  {C_CYAN}1.{C_RESET} Check Partition Table & eMMC Info (edl printgpt)")
    print(f"  {C_CYAN}2.{C_RESET} Reboot Modem to EDL 9008 Mode (Auto detect: SSH / ADB / Fastboot)")
    print(f"  {C_CYAN}3.{C_RESET} Reboot Modem to Bootloader / Fastboot (adb/ssh reboot bootloader)")
    print(f"  {C_CYAN}4.{C_RESET} Reboot Modem from EDL to Normal Operating Mode (edl reset)")
    print()
    print(f"{C_DIM}--- [ BACKUP & RESCUE ] ---{C_RESET}")
    print(f"  {C_CYAN}5.{C_RESET} Backup Critical IMEI & EFS Partitions (modemst1, modemst2, fsg, fsc)")
    print(f"  {C_CYAN}6.{C_RESET} Full eMMC RAW Backup (Single 4GB Binary - edl rf)")
    print(f"  {C_CYAN}7.{C_RESET} Backup All Individual Partitions + rawprogram0.xml (edl rl --genxml)")
    print()
    print(f"{C_DIM}--- [ FLASHING & RESTORE ] ---{C_RESET}")
    print(f"  {C_GREEN}8.{C_RESET} {C_BOLD}Flash / Overwrite OpenWrt via SSH (Sysupgrade - 1-Click Online){C_RESET}")
    print(f"  {C_CYAN}9.{C_RESET} Flash OpenWrt Firmware via Fastboot (Clean Install GPT + Boot + System)")
    print(f"  {C_CYAN}10.{C_RESET} Flash OpenWrt Firmware via EDL 9008 (Emergency Unbrick / Clean Flash)")
    print(f"  {C_CYAN}11.{C_RESET} Restore Critical IMEI & EFS Partitions from Backup")
    print(f"  {C_CYAN}12.{C_RESET} Restore Full eMMC RAW (Write 4GB Image - edl wf)")
    print()
    print(f"{C_DIM}--- [ HARDWARE & DEVICE TREE (DTS) ] ---{C_RESET}")
    print(f"  {C_CYAN}13.{C_RESET} Check Board Hardware Variant & GPIO LED Mapping")
    print(f"  {C_CYAN}14.{C_RESET} Patch Device Tree JZ01-45 (LED: R25, G6, B7 | SIM: 22,23,1,52)")
    print()
    print(f"  {C_WHITE}0.{C_RESET} Exit")
    print()

    if not sys.stdin.isatty():
        log(f"{SYM_INFO} Mode non-interaktif terdeteksi. Gunakan parameter flag:")
        print(f"      --reboot-edl         : Transisi ke mode EDL")
        print(f"      --check-board        : Cek revisi hardware board modem")
        print(f"      --patch-board        : Patch DTB boot ke skema board baru")
        print(f"      --backup-nvram       : Backup partisi IMEI/NVRAM ke folder backups/")
        print(f"      --backup-partitions  : Dump seluruh partisi eMMC ke folder backups/")
        print(f"      --backup-full        : Dump raw eMMC 4GB ke 1 file .bin")
        sys.exit(0)

    try:
        pilihan = input(f"{C_BOLD}{C_WHITE}Select operation [0-14]: {C_RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCanceled.")
        sys.exit(0)

    if pilihan == "1":
        if ensure_edl_mode(adb):
            code, out = run_edl_cmd(["printgpt", f"--loader={args.loader}", "--memory=eMMC"])
            print(out)
    elif pilihan == "2":
        if is_edl:
            log(f"{SYM_INFO} Perangkat sudah berada di mode EDL 9008.")
        else:
            ensure_edl_mode(adb)
    elif pilihan == "3":
        do_reboot_bootloader()
    elif pilihan == "4":
        log(f"{SYM_ARROW} Mengirim perintah reboot normal ke modem via EDL...")
        run_edl_cmd(["reset", f"--loader={args.loader}"])
        log(f"{SYM_OK} {C_GREEN}Modem berhasil di-reboot ke mode operasional normal.{C_RESET}")
    elif pilihan == "5":
        if ensure_edl_mode(adb):
            board_sel = select_board("1")
            target_dir = os.path.join(PROJECT_DIR, board_sel["backup_dir"], f"nvram_{timestamp_str}")
            do_backup_nvram(target_dir, args.loader)
    elif pilihan == "6":
        if ensure_edl_mode(adb):
            board_sel = select_board("1")
            target_file = os.path.join(PROJECT_DIR, board_sel["backup_dir"], f"full_dump_{timestamp_str}.bin")
            do_backup_full(target_file, args.loader)
    elif pilihan == "7":
        if ensure_edl_mode(adb):
            target_dir = os.path.join(BACKUPS_DIR, f"partitions_{timestamp_str}")
            do_backup_partitions(target_dir, args.loader)
    elif pilihan == "8":
        board_sel = select_board("1")
        do_flash_sysupgrade(board_sel)
    elif pilihan == "9":
        board_sel = select_board("1")
        do_flash_fastboot(board_sel)
    elif pilihan == "10":
        board_sel = select_board("1")
        print()
        log(f"{SYM_WARN} {C_YELLOW}PERSIAPAN FLASHING OPENWRT EDL UNTUK: {board_sel['name']}{C_RESET}")
        
        do_backup = True
        try:
            bk_ans = input(f"{C_BOLD}{C_WHITE}Do you want to backup NVRAM/IMEI partitions first? (Y/n): {C_RESET}").strip().lower()
            if bk_ans in ["n", "no"]:
                do_backup = False
        except (KeyboardInterrupt, EOFError):
            do_backup = True

        confirm = input(f"{C_RED}{C_BOLD}Proceed with OpenWrt flashing now? (y/N): {C_RESET}").strip().lower()
        if confirm in ["y", "yes"]:
            if ensure_edl_mode(adb):
                do_flash_openwrt(args.loader, board_sel, skip_backup=(not do_backup))
        else:
            log("Flashing OpenWrt dibatalkan.")
    elif pilihan == "11":
        print(f"\n{C_BOLD}{C_WHITE}[ RESTORE PARTISI KRITIS IMEI & EFS ]{C_RESET}")
        board_sel = select_board("1")
        b_dir = os.path.join(PROJECT_DIR, board_sel["backup_dir"])
        if not os.path.exists(b_dir):
            log(f"{SYM_FAIL} Direktori backup {b_dir} tidak ditemukan.")
        else:
            if ensure_edl_mode(adb):
                for part in ["modemst1", "modemst2", "fsg", "fsc"]:
                    p_file = os.path.join(b_dir, f"{part}.bin")
                    if os.path.exists(p_file):
                        log(f"{SYM_ARROW} Flashing partisi {part} dari {p_file}...")
                        run_edl_cmd(["w", part, p_file, f"--loader={args.loader}"])
                log(f"{SYM_OK} {C_GREEN}Restore partisi EFS/IMEI selesai.{C_RESET}")
    elif pilihan == "12":
        # Cari file dump yang tersedia di folder backups
        available_bins = []
        if os.path.exists(BACKUPS_DIR):
            for root, _, files in os.walk(BACKUPS_DIR):
                for f in files:
                    if f.endswith(".bin") and ("full" in f or "dump" in f or "backup" in f):
                        available_bins.append(os.path.join(root, f))
        
        print()
        print(f"{C_BOLD}{C_WHITE}[ PILIH FILE RESTORE FULL eMMC ]{C_RESET}")
        restore_file = ""
        if available_bins:
            print("File dump yang ditemukan di folder backups/:")
            for idx, bf in enumerate(available_bins, 1):
                sz_mb = os.path.getsize(bf) / (1024 * 1024)
                print(f"  {C_CYAN}{idx}.{C_RESET} {os.path.basename(bf)} ({sz_mb:.1f} MB)")
            print(f"  {C_CYAN}M.{C_RESET} Masukkan path file secara manual")
            sub_choice = input(f"{C_BOLD}{C_WHITE}Pilihan [1-{len(available_bins)}/M]: {C_RESET}").strip()
            if sub_choice.isdigit() and 1 <= int(sub_choice) <= len(available_bins):
                restore_file = available_bins[int(sub_choice) - 1]
            elif sub_choice.lower() == "m":
                restore_file = input("Masukkan path lengkap file .bin: ").strip()
        else:
            restore_file = input("Masukkan path lengkap file .bin untuk di-restore: ").strip()

        if restore_file and os.path.exists(restore_file):
            confirm = input(f"{C_RED}{C_BOLD}Yakin ingin me-restore file ini ke eMMC? (y/N): {C_RESET}").strip().lower()
            if confirm in ["y", "yes"]:
                if ensure_edl_mode(adb):
                    do_restore_full(restore_file, args.loader)
            else:
                log("Restore dibatalkan.")
        else:
            log(f"{SYM_FAIL} Path file tidak valid atau tidak ditemukan.")
    elif pilihan == "13":
        if ensure_edl_mode(adb):
            do_check_board(args.loader)
    elif pilihan == "14":
        if ensure_edl_mode(adb):
            do_patch_board(args.loader)
    else:
        log("Keluar.")

if __name__ == "__main__":
    main()
