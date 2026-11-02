#!/bin/sh
# Runs inside a fresh debian:trixie container. Mounts: /debs (built debs and tests.list).
export DEBIAN_FRONTEND=noninteractive
fail=0
ok()   { echo "  ok   $*"; }
bad()  { echo "  FAIL $*"; fail=1; }
check() { desc="$1"; shift; if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi; }

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
done < /debs/tests.list

# Remove and purge in reverse dependency order (tui depends on tetron).
for name in $(for n in $installed; do echo $n; done | tac); do
	echo "== remove/purge $name"
	check "dpkg -r" dpkg -r "$name"
	check "dpkg -P" dpkg -P "$name"
	check "files gone" sh -c "! dpkg -L $name"
done
[ $fail = 0 ] && echo "ALL PASS" || echo "FAILURES"
exit $fail
