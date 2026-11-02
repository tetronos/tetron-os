#!/bin/sh
# Boot a live ISO in QEMU/KVM, wait for the serial login prompt of host tetron,
# save a VGA screenshot and power off.
# Usage: tests/boot-live.sh ISO [bios|uefi] [timeout-seconds]
# Output: out/boot-<fw>.log (serial), out/boot-<fw>.png (VGA). Exit 0 when
# the serial log shows the tetron login prompt.
set -e
ISO="$1"; FW="${2:-bios}"; TIMEOUT="${3:-240}"
[ -f "$ISO" ] || { echo "usage: $0 ISO [bios|uefi] [timeout]" >&2; exit 2; }
OUT="$(cd "$(dirname "$0")/.." && pwd)/out"
mkdir -p "$OUT"
LOG="$OUT/boot-$FW.log"; PNG="$OUT/boot-$FW.png"
TMP=$(mktemp -d); QMP="$TMP/qmp.sock"
trap 'kill $QEMU_PID 2>/dev/null; rm -rf "$TMP"' EXIT
rm -f "$LOG" "$PNG"

case "$FW" in
	bios) FWARGS="" ;;
	uefi) cp /usr/share/OVMF/OVMF_VARS_4M.fd "$TMP/vars.fd"
	      FWARGS="-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd -drive if=pflash,format=raw,file=$TMP/vars.fd" ;;
	*) echo "firmware must be bios or uefi" >&2; exit 2 ;;
esac

# shellcheck disable=SC2086
qemu-system-x86_64 -enable-kvm -cpu host -m 2048 -smp 2 $FWARGS \
	-drive file="$ISO",media=cdrom,readonly=on -boot d \
	-device virtio-vga -display none -nic user,model=virtio-net-pci \
	-serial file:"$LOG" -qmp unix:"$QMP",server=on,wait=off &
QEMU_PID=$!

qmp() {  # qmp '{"execute": ...}' : one command on a fresh QMP connection
	python3 -I -c '
import json, socket, sys
s = socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); f = s.makefile("rw")
f.readline(); f.write(json.dumps({"execute": "qmp_capabilities"}) + "\n"); f.flush(); f.readline()
f.write(sys.argv[2] + "\n"); f.flush()
while True:
    r = json.loads(f.readline())
    if "return" in r or "error" in r:
        print(json.dumps(r)); break
' "$QMP" "$1"
}

# The boot menu may wait for a key; Enter picks the default entry.
sleep 8
qmp '{"execute": "send-key", "arguments": {"keys": [{"type": "qcode", "data": "ret"}]}}' >/dev/null || true

t=0; ok=1
while [ $t -lt "$TIMEOUT" ]; do
	if grep -aq '^tetron login:' "$LOG" 2>/dev/null; then ok=0; break; fi
	sleep 5; t=$((t + 5))
done
# Give kmscon and tetron-wm time to draw before the screenshot.
[ $ok = 0 ] && sleep 20
qmp "{\"execute\": \"screendump\", \"arguments\": {\"filename\": \"$PNG\", \"format\": \"png\"}}" >/dev/null || true
qmp '{"execute": "quit"}' >/dev/null 2>&1 || true
wait $QEMU_PID 2>/dev/null || true

if [ $ok = 0 ]; then echo "PASS $FW: serial login prompt after ${t}s; screenshot $PNG"
else echo "FAIL $FW: no tetron login prompt on serial within ${TIMEOUT}s; see $LOG and $PNG"; fi
exit $ok
