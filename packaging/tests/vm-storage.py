#!/usr/bin/env python3
"""tetronos-storage in a VM: a user in group users mounts, unmounts and powers off drives with
udisksctl, no sudo, from a serial console login (not an active seat session, like kmscon and ssh).
Usage: packaging/tests/vm-storage.py ISO DEB   (a live ISO; DEB the tetronos-storage .deb; needs kvm, qemu)
Drives: an exFAT USB stick (usb-storage) and an ext4 SATA disk. Work dir: DO-NOT-COMMIT/work/vm-storage."""
import os, re, shutil, socket, subprocess, sys, time

iso, deb = (os.path.abspath(a) for a in sys.argv[1:3])
here = os.path.dirname(os.path.abspath(__file__))
w = os.path.join(here, "..", "..", "DO-NOT-COMMIT", "work", "vm-storage"); os.makedirs(w, exist_ok=True)
stamp = int(time.time())
usb, sata, carry, sock = (f"{w}/{n}-{stamp}" for n in ("usb.raw", "sata.raw", "carry.raw", "ser.sock"))

def part(img, size, mkfs):
    """One partition at 1 MiB, made with mkfs on an offset image (no root needed)."""
    subprocess.run(["truncate", "-s", size, img], check=True)
    subprocess.run(["sfdisk", "-q", img], input=b"label: gpt\n,\n", check=True)
    p = f"{img}.p1"; subprocess.run(["truncate", "-s", str(os.path.getsize(img) - 2 * 1024 * 1024), p], check=True)
    subprocess.run([*mkfs, p], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["dd", f"if={p}", f"of={img}", "bs=1M", "seek=1", "conv=notrunc", "status=none"], check=True); os.remove(p)

part(usb, "64M", ["mkfs.exfat", "-L", "STICK"])
part(sata, "64M", ["mke2fs", "-q", "-t", "ext4", "-L", "data"])
d = f"{w}/carry-{stamp}"; os.makedirs(d); shutil.copy(deb, d)
subprocess.run(["mke2fs", "-q", "-t", "ext4", "-L", "carry", "-d", d, carry, "32M"], check=True); shutil.rmtree(d)

q = subprocess.Popen(["qemu-system-x86_64", "-enable-kvm", "-cpu", "host", "-m", "2048", "-smp", "2",
    "-drive", f"file={iso},media=cdrom,readonly=on", "-boot", "d",
    "-device", "ahci,id=ahci", "-drive", f"file={sata},format=raw,if=none,id=sata", "-device", "ide-hd,drive=sata,bus=ahci.0,serial=SATADISK",
    "-device", "qemu-xhci", "-drive", f"file={usb},format=raw,if=none,id=usb", "-device", "usb-storage,drive=usb,removable=on,serial=USBSTICK",
    "-drive", f"file={carry},format=raw,if=virtio",
    "-display", "none", "-nic", "user,model=virtio-net-pci", "-serial", f"unix:{sock},server=on,wait=off"])
fails = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name, flush=True)
    if not ok: fails.append(name)
try:
    for _ in range(50):
        if os.path.exists(sock): break
        time.sleep(0.2)
    s = socket.socket(socket.AF_UNIX); s.connect(sock); s.settimeout(1)
    buf = ""
    def expect(rx, timeout):
        global buf
        end = time.time() + timeout
        while time.time() < end:
            m = re.search(rx, buf)
            if m:
                out, buf = buf[:m.end()], buf[m.end():]; return out
            try: buf += s.recv(65536).decode(errors="replace")
            except socket.timeout: pass
        raise SystemExit(f"timeout waiting for {rx!r}; tail: {buf[-400:]!r}")
    def send(t): s.sendall(t.encode())
    expect(r"login:", 240); send("tetronos\n"); expect(r"Password:", 20); send("live\n"); expect(r"\$ ", 60)
    n = [0]
    def run(cmd, timeout=60):
        n[0] += 1; tag = f"M{n[0]}X"
        send(f"{cmd}; echo {tag}$?\n")
        out = expect(tag + r"\d+", timeout)
        rc = int(re.search(tag + r"(\d+)", out).group(1)); expect(r"\$ ", 10)
        if os.environ.get("V"): print("---", cmd[:70], "\n", out[-600:], flush=True)
        return rc, out
    def dev(serial):
        _, out = run(f"lsblk -dno NAME,SERIAL | awk '$2==\"{serial}\"{{print \"/dev/\"$1\"1\"}}'")
        m = re.search(r"(/dev/[a-z]+1)\r", out); return m.group(1) if m else "/dev/missing"
    rc, out = run("id -nG"); check("live user is in group users", " users" in out or "users " in out)
    run("sudo mount -o ro /dev/vda /mnt && sudo cp /mnt/*.deb /run/ && sudo umount /mnt")
    rc, out = run("sudo apt-get update -qq 2>&1 | tail -2; sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq /run/tetronos-storage_*.deb 2>&1 | tail -3", 900)
    check("tetronos-storage installs with its Depends", rc == 0)
    rc, out = run("ls /usr/share/polkit-1/rules.d/50-tetronos-storage.rules && command -v udisksctl mkfs.exfat mkfs.vfat ntfs-3g")
    check("rule and tools present", rc == 0)
    rc, out = run("loginctl show-session $XDG_SESSION_ID -p Active -p Seat 2>&1 | tr '\\n' ' '")
    print("session:", out.splitlines()[-1] if out else "", flush=True)
    rc, out = run("systemctl is-active polkit udisks2; systemctl status polkit --no-pager -n 8 2>&1 | tail -12")
    check("polkit runs after the install", rc == 0)
    rc, out = run("N=$(findmnt -rn -o TARGET | grep -c ^/media/); echo media=$N")
    check("nothing automounted", "media=0" in out)
    stick, disk = dev("USBSTICK"), dev("SATADISK")
    rc, out = run(f"udisksctl mount --no-user-interaction -b {stick}", 30)
    check("USB stick (exFAT) mounts without sudo", rc == 0 and "/media/tetronos/STICK" in out)
    rc, out = run("echo hi > /media/tetronos/STICK/t && cat /media/tetronos/STICK/t")
    check("the user writes to the mounted stick", rc == 0)
    rc, out = run(f"udisksctl unmount --no-user-interaction -b {stick}", 30); check("stick unmounts", rc == 0)
    rc, out = run(f"udisksctl power-off --no-user-interaction -b {stick[:-1]}", 30); check("stick powers off", rc == 0)
    rc, out = run(f"udisksctl mount --no-user-interaction -b {disk}", 30)
    check("internal SATA disk (ext4) mounts without sudo", rc == 0 and "/media/tetronos/data" in out)
    rc, out = run(f"udisksctl unmount --no-user-interaction -b {disk}", 30); check("SATA disk unmounts", rc == 0)
    rc, out = run(f"udisksctl unmount --no-user-interaction -b $(findmnt -no SOURCE /run/live/medium) 2>&1", 30)
    check("the live medium (a system mount) is not unmountable", rc != 0)
    send("sudo systemctl poweroff\n")
    try: q.wait(timeout=120)
    except subprocess.TimeoutExpired: q.kill(); q.wait()
finally:
    if q.poll() is None: q.kill(); q.wait()
print(f"{'FAIL' if fails else 'PASS'}: {len(fails)} failed", flush=True)
sys.exit(1 if fails else 0)
