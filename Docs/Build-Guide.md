# Customizing & Building OpenWrt from Source

Panduan lengkap cara mengompilasi firmware OpenWrt dari source code untuk Qualcomm Snapdragon 410 (MSM8916), memodifikasi konfigurasi kernel, menambahkan driver LED trigger (seperti `netdev`), dan menyesuaikan Device Tree (DTS).

---

## 1. Arsitektur Build MSM8916 OpenWrt

Target OpenWrt untuk modem MSM8916 berbasis kernel Linux modern (6.12+):
- **Base OpenWrt**: `openwrt/openwrt` (Branch `v25.12.x` atau master).
- **Target Linux**: `target/linux/msm89xx` (arsitektur `aarch64`).
- **Board Profile**: `yiming-uz801v3` (digunakan juga untuk varian UZ801, JZ0145, dan clone 4G dongle).
- **Kernel Image**: `boot.img` (menggabungkan kernel Image-gz + appended DTB).
- **Root Filesystem**: SquashFS (`system.img`) dengan overlay data terpisah.

---

## 2. Persiapan Environment Build (Host Linux / Ubuntu)

OpenWrt build system membutuhkan sistem operasi Linux (Ubuntu 22.04 LTS / 24.04 LTS atau Debian 12 direkomendasikan):

```bash
# 1. Update paket dan instal build-essential
sudo apt update
sudo apt install -y build-essential clang flex bison g++ gawk gcc-multilib \
  g++-multilib gettext git libncurses-dev libssl-dev python3-setuptools \
  rsync swig unzip zlib1g-dev file wget curl
```

> **Catatan untuk pengguna macOS**: Sangat disarankan menggunakan GitHub Actions (metode Cloud Build di repo ini) atau VM Ubuntu di UTM/Parallels karena filesystem case-sensitive dan toolchain multilib cross-compiler OpenWrt dirancang untuk Linux.

---

## 3. Langkah Clone & Setup Source Code

```bash
# 1. Clone repository resmi OpenWrt
git clone https://git.openwrt.org/openwrt/openwrt.git openwrt
cd openwrt
git checkout v25.12.5

# 2. Ambil target msm89xx dari upstream maintainer
git clone https://github.com/hkfuertes/msm8916-openwrt.git upstream-msm
chmod +x upstream-msm/apply_patches.sh
./upstream-msm/apply_patches.sh .

# Pindahkan file target dan packages
mv upstream-msm/msm89xx target/linux/msm89xx
mv upstream-msm/packages package/msm8916
mv upstream-msm/diffconfig_uz801 .config
```

---

## 4. Cara Kustomisasi & Modifikasi

### A. Mengaktifkan Driver / Modul Kernel (Contoh: LED Netdev Trigger)
File konfigurasi kernel berada di `target/linux/msm89xx/config-6.12`.

Untuk mengaktifkan trigger LED jaringan agar LED modem bisa berkedip mengikuti paket Rx/Tx:
1. Buka file:
   ```bash
   nano target/linux/msm89xx/config-6.12
   ```
2. Cari baris `# CONFIG_LEDS_TRIGGER_NETDEV is not set`, ganti menjadi:
   ```text
   CONFIG_LEDS_TRIGGER_NETDEV=y
   CONFIG_LEDS_TRIGGER_ACTIVITY=y
   CONFIG_LEDS_TRIGGER_TIMER=y
   CONFIG_LEDS_TRIGGER_HEARTBEAT=y
   CONFIG_LEDS_TRIGGER_DEFAULT_ON=y
   ```
3. Di repo ini, proses tersebut sudah diotomatisasi menggunakan script:
   ```bash
   python3 openwrt-build/scripts/apply_kernel_config.py \
     target/linux/msm89xx/config-6.12 \
     openwrt-build/kernel-config/led-triggers.conf
   ```

### B. Modifikasi Device Tree (DTS) untuk Board Baru (Contoh: JZ0145)
Board JZ0145 memiliki pinout LED dan saklar SIM card multiplexer yang berbeda dari UZ801 lama:
- **Red LED**: GPIO 25
- **Green LED**: GPIO 6
- **Blue LED**: GPIO 7
- **SIM Multiplexer**: GPIO 22, 23, 1
- **SIM Detect**: GPIO 52

Patch DTS diletakkan di `target/linux/msm89xx/patches-6.12/910-jz0145-leds-sim.patch`. Kernel build system OpenWrt akan otomatis menerapkan patch tersebut saat proses compile.

### C. Menambah / Mengurangi Paket di LuCI
Jalankan menu interaktif OpenWrt:
```bash
make menuconfig
```
- Masuk ke menu **Kernel modules -> LED modules** untuk memilih `kmod-ledtrig-netdev`.
- Masuk ke menu **LuCI -> Collections / Applications** untuk menambah Web UI (`luci-app-firewall`, `luci-app-ttyd`, dsb).
- Setelah selesai, simpan (`<Save>`) ke `.config`.

---

## 5. Proses Kompilasi Firmware

```bash
# 1. Update dan install feeds packages
./scripts/feeds update -a
./scripts/feeds install -a

# 2. Sinkronisasi konfigurasi dan unduh sumber paket
make defconfig
make download -j8

# 3. Kompilasi firmware (-j disesuaikan dengan jumlah core CPU)
make -j$(nproc)
```

Jika terjadi error kompilasi dan ingin melihat log detailnya:
```bash
make -j1 V=s
```

---

## 6. Output Binary Hasil Build

Setelah compile selesai, seluruh binary firmware akan tersimpan di:
`bin/targets/msm89xx/msm8916/`

File penting yang dihasilkan:
1. `openwrt-msm89xx-msm8916-squashfs-boot.img` : Kernel Linux + DTB hardware.
2. `openwrt-msm89xx-msm8916-squashfs-system.img` : Root filesystem OpenWrt.
3. `openwrt-msm89xx-msm8916-squashfs-gpt_both0.bin` : Tabel partisi GPT.

---

## 7. Cara Otomatis: Build Melalui GitHub Actions (Cloud)

Anda tidak perlu menginstal environment Linux di komputer lokal. Repo ini sudah dilengkapi workflow otomatis:

1. Buka menu **Actions** di repo GitHub Anda.
2. Pilih workflow **Build JZ0145 (netdev LED)**.
3. Klik tombol **Run workflow** -> pilih branch `main`.
4. Tunggu ~30–45 menit sampai proses selesai.
5. Unduh file zip artifact firmware (`openwrt_jz0145_netdev_...`) yang langsung siap diflash ke modem via `flasher.py`.
