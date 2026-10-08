# Base Image Linux untuk Build OpenWrt MSM8916
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Jakarta

# 1. Install Full Build Toolchain & Dependencies Host
RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    flex \
    bison \
    g++ \
    gawk \
    gettext \
    git \
    libncurses-dev \
    libssl-dev \
    python3-setuptools \
    python3-dev \
    python3-pip \
    rsync \
    swig \
    unzip \
    zlib1g-dev \
    file \
    wget \
    curl \
    device-tree-compiler \
    mkbootimg \
    subversion \
    sudo \
    locales \
    fdisk \
    gcc-arm-none-eabi \
    python3-cryptography \
    python3-pycryptodome \
    python3-pyasn1-modules \
    bc \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# OpenWrt tidak boleh di-build sebagai root
RUN useradd -m -s /bin/bash builder && \
    echo "builder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER builder
WORKDIR /home/builder/openwrt

CMD ["/bin/bash"]
