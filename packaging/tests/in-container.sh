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
	[ "$name" = tetronos-branding ] && {
		for f in issue issue.net motd; do
			check "/etc/$f is TetronOS" grep -q TetronOS /etc/$f
			check "/etc/$f.debian kept" test -e /etc/$f.debian
		done
	}
	[ "$name" = tetronos-base-config ] && {
		for d in Desktop Documents Downloads Pictures; do check "/etc/skel/$d created" test -d /etc/skel/$d; done
		check "ping sysctl drop-in installed" grep -q '^net.ipv4.ping_group_range = 0 2147483647$' /usr/lib/sysctl.d/50-tetronos-ping.conf
	}
	[ "$name" = tetronos-live-config ] && {
		check "live-ssh-password writes no while an account has the live password" sh -c 'useradd -p "$(perl -e "print crypt(q(live), q(8A))")" livetest && /usr/libexec/tetronos/live-ssh-password >/dev/null && grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config.d/40-tetronos-live-password.conf'
		check "live-ssh-password writes yes once no account has it" sh -c 'userdel livetest && /usr/libexec/tetronos/live-ssh-password >/dev/null && grep -q "^PasswordAuthentication yes" /etc/ssh/sshd_config.d/40-tetronos-live-password.conf'
		rm -f /etc/ssh/sshd_config.d/40-tetronos-live-password.conf
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
	[ "$name" = tetronos-branding ] && {
		check "/etc/issue is Debian again" grep -q Debian /etc/issue
		check "/etc/motd is Debian again" grep -q Debian /etc/motd
		check "no diversions left" sh -c "! dpkg-divert --list tetronos-branding | grep -q ."
	}
	[ "$name" = tetronos-base-config ] && {
		check "empty /etc/skel folders removed" sh -c '! test -e /etc/skel/Desktop'
	}
	[ "$name" = tetronos-live-config ] && {
		check "getty@tty1 enabled again" systemctl is-enabled getty@tty1.service
		check "kmsconvt@tty1 not enabled" sh -c '! systemctl is-enabled kmsconvt@tty1.service'
	}
done
[ $fail = 0 ] && echo "ALL PASS" || echo "FAILURES"
exit $fail
