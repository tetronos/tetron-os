#!/bin/sh
# Build-VM manager: a Debian 13 cloud image under QEMU/KVM with live-build installed.
# Usage: vm.sh create|start|stop|status|ssh [cmd...]|sync|pull|destroy
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VMDIR="${VMDIR:-$ROOT/build/vm}"
PORT="${VM_PORT:-2222}"
CPUS="${VM_CPUS:-6}"
MEM="${VM_MEM:-8G}"
DISK="${VM_DISK:-40G}"
IMG_URL=https://cloud.debian.org/images/cloud/trixie/latest
IMG=debian-13-genericcloud-amd64.qcow2
KEY="$VMDIR/id_ed25519"
SSH_OPTS="-i $KEY -p $PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=5"

ssh_vm() { ssh $SSH_OPTS builder@127.0.0.1 "$@"; }
running() { [ -f "$VMDIR/qemu.pid" ] && kill -0 "$(cat "$VMDIR/qemu.pid")" 2>/dev/null; }

create() {
	mkdir -p "$VMDIR"
	[ -f "$VMDIR/disk.qcow2" ] && { echo "vm exists: $VMDIR (use destroy first)" >&2; exit 1; }
	if [ ! -f "$VMDIR/$IMG" ]; then
		curl -fsSL -o "$VMDIR/$IMG" "$IMG_URL/$IMG"
		sum=$(curl -fsL "$IMG_URL/SHA512SUMS" | awk -v f="$IMG" '$2 == f {print $1}')
		echo "$sum  $VMDIR/$IMG" | sha512sum -c -
	fi
	[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N "" -C tetronos-builder -f "$KEY"
	qemu-img create -q -f qcow2 -F qcow2 -b "$VMDIR/$IMG" "$VMDIR/disk.qcow2" "$DISK"
	cat > "$VMDIR/user-data" <<UD
#cloud-config
hostname: tetronos-builder
users:
  - name: builder
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys:
      - $(cat "$KEY.pub")
package_update: true
packages: [live-build, debootstrap, xorriso, squashfs-tools, mtools, dosfstools, cpio, make, rsync,
  grub-pc-bin, grub-efi-amd64-bin, grub-efi-amd64-signed, shim-signed, isolinux, syslinux,
  syslinux-common, ca-certificates, gnupg, procps]
runcmd:
  - touch /var/lib/tetronos-builder-ready
UD
	printf 'instance-id: tetronos-builder\nlocal-hostname: tetronos-builder\n' > "$VMDIR/meta-data"
	xorriso -as mkisofs -quiet -o "$VMDIR/seed.iso" -V cidata -J -r "$VMDIR/user-data" "$VMDIR/meta-data"
	start
	echo "waiting for cloud-init (installs live-build)..."
	i=0
	until ssh_vm test -f /var/lib/tetronos-builder-ready 2>/dev/null; do
		i=$((i + 1)); [ $i -gt 120 ] && { echo "timeout; see $VMDIR/console.log" >&2; exit 1; }
		sleep 5
	done
	echo "vm ready"
}

start() {
	running && return 0
	qemu-system-x86_64 -enable-kvm -cpu host -smp "$CPUS" -m "$MEM" \
		-drive file="$VMDIR/disk.qcow2",if=virtio,format=qcow2 \
		-drive file="$VMDIR/seed.iso",if=virtio,format=raw,readonly=on \
		-nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:"$PORT"-:22 \
		-display none -serial file:"$VMDIR/console.log" \
		-daemonize -pidfile "$VMDIR/qemu.pid"
	i=0
	until ssh_vm true 2>/dev/null; do
		i=$((i + 1)); [ $i -gt 60 ] && { echo "ssh timeout" >&2; exit 1; }
		sleep 3
	done
}

stop() {
	running || return 0
	ssh_vm sudo poweroff 2>/dev/null || true
	i=0
	while running && [ $i -lt 30 ]; do i=$((i + 1)); sleep 1; done
	running && kill "$(cat "$VMDIR/qemu.pid")" || true
}

case "${1:-}" in
	create) create ;;
	start) start ;;
	stop) stop ;;
	status) running && echo running || echo stopped ;;
	ssh) shift; ssh_vm "$@" ;;
	sync) rsync -a --delete -e "ssh $SSH_OPTS" --exclude build --exclude out --exclude .git --exclude DO-NOT-COMMIT "$ROOT/" builder@127.0.0.1:src/ ;;
	pull) mkdir -p "$ROOT/out"; rsync -a -e "ssh $SSH_OPTS" builder@127.0.0.1:out/ "$ROOT/out/" ;;
	destroy) stop; rm -rf "$VMDIR" ;;
	*) echo "usage: $0 create|start|stop|status|ssh|sync|pull|destroy" >&2; exit 2 ;;
esac
