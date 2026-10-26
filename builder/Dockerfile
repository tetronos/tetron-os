FROM debian:trixie
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    live-build debootstrap xorriso squashfs-tools mtools dosfstools cpio make \
    grub-pc-bin grub-efi-amd64-bin grub-efi-amd64-signed shim-signed \
    isolinux syslinux syslinux-common ca-certificates gnupg procps \
    && rm -rf /var/lib/apt/lists/*
