FROM ubuntu:22.04 AS base

LABEL maintainer="OpenWrt Builder"

# Install required dependencies
COPY devenv/dependencies.sh /install_dependencies
RUN chmod +x /install_dependencies && \
    /install_dependencies && \
    rm -rf /install_dependencies

# Create a non-root user with sudo access (no password required)
RUN useradd -m -u 1000 -G sudo builder && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER builder
WORKDIR /home/builder

FROM base AS openwrt

ARG OPENWRT_VERSION=v25.12.5

# Clone OpenWrt repository
RUN git clone --depth 1 -b ${OPENWRT_VERSION} https://git.openwrt.org/openwrt/openwrt.git openwrt

# Apply mac80211 patches (wcn36xx/ath10k-sdio support)
COPY --chmod=755 apply_patches.sh ./
RUN ./apply_patches.sh openwrt

# Pre-build host tools inside Docker image so container starts with a complete toolchain
RUN cd openwrt && \
    make defconfig && \
    make -j$(nproc) tools/install && \
    make -j$(nproc) toolchain/install && \
    rm -rf tmp

# Update and install feeds
RUN cd openwrt && \
    ./scripts/feeds update -a && \
    ./scripts/feeds install -a && \
    rm -rf tmp

WORKDIR /home/builder/openwrt

CMD ["/bin/bash"]
