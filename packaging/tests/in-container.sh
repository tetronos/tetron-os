#!/bin/sh
# Runs inside a fresh debian:trixie container. Mounts: /debs (built debs and tests.list).
export DEBIAN_FRONTEND=noninteractive
fail=0
ok()   { echo "  ok   $*"; }
bad()  { echo "  FAIL $*"; fail=1; }
check() { desc="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi; }

# kmscon (tetronos-core) is only in trixie-backports: same source and pin as the ISO.
echo "deb http://deb.debian.org/debian trixie-backports main" > /etc/apt/sources.list.d/backports.list
cp /kmscon-backports.pref /etc/apt/preferences.d/kmscon-backports.pref
# CPU microcode (tetronos-desktop) is in non-free-firmware, like on the ISO.
sed -i 's/^Components: main$/Components: main non-free-firmware/' /etc/apt/sources.list.d/debian.sources
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends systemd >/dev/null 2>&1

while IFS='|' read -r name version smoke; do
	deb=$(ls /debs/${name}_${version}_*.deb 2>/dev/null | head -1)
	echo "== $name $version"
	[ -n "$deb" ] || { bad "deb not found"; continue; }
	if apt-get install -y -qq --no-install-recommends "$deb" >/tmp/apt.log 2>&1; then ok "apt install resolves Depends"; installed="$installed $name"
	else bad "apt install"; tail -5 /tmp/apt.log; continue; fi
	check "dpkg status ii" sh -c "dpkg -s $name | grep -q 'Status: install ok installed'"
	dpkg -L "$name" | while read -r f; do [ -d "$f" ] || [ -e "$f" ] || echo "missing $f"; done | grep -q . && bad "listed files exist" || ok "listed files exist"
	check "md5sums verify" dpkg --verify "$name"
	if [ -n "$smoke" ]; then
		out=$(sh -c "$smoke" 2>&1)
		echo "$out" | grep -q "${version%-*}" && ok "smoke: $smoke -> $out" || bad "smoke: $smoke -> $out"
	fi
	for u in $(dpkg -L "$name" | grep '^/usr/lib/systemd/system/.*\.service$'); do
		check "systemd-analyze verify $u" systemd-analyze verify "$u"
		check "unit not enabled by package" sh -c "! [ -e /etc/systemd/system/multi-user.target.wants/$(basename "$u") ]"
	done
	[ "$name" = tetron ] && {
		check "group tetron created" getent group tetron
		check "no /etc/tetron created at install" sh -c '! [ -e /etc/tetron ]'
		check "no identity created" sh -c '! [ -e /etc/tetron/secret_key ]'
	}
	[ "$name" = tetronos-desktop-config ] && {
		check "polkit rules installed" test -f /usr/share/polkit-1/rules.d/50-tetronos-desktop.rules
	}
	[ "$name" = tetronos-live-config ] && {
		check "kmsconvt@tty1 enabled" systemctl is-enabled kmsconvt@tty1.service
		check "getty@tty1 disabled" sh -c '! systemctl is-enabled getty@tty1.service'
		check "kmscon drop-in parses" systemd-analyze verify --man=no kmsconvt@tty1.service
		check "profile.d hook parses" sh -n /etc/profile.d/tetronos-session.sh
		check "profile.d hook is a conffile" sh -c "dpkg-query -W -f '\${Conffiles}' tetronos-live-config | grep -q tetronos-session.sh"
	}
done < /debs/tests.list

# Remove and purge in reverse dependency order (tui depends on tetron).
for name in $(for n in $installed; do echo $n; done | tac); do
	echo "== remove/purge $name"
	check "dpkg -r" dpkg -r "$name"
	check "dpkg -P" dpkg -P "$name"
	check "files gone" sh -c "! dpkg -L $name"
	[ "$name" = tetronos-live-config ] && {
		check "getty@tty1 enabled again" systemctl is-enabled getty@tty1.service
		check "kmsconvt@tty1 not enabled" sh -c '! systemctl is-enabled kmsconvt@tty1.service'
	}
done
[ $fail = 0 ] && echo "ALL PASS" || echo "FAILURES"
exit $fail
