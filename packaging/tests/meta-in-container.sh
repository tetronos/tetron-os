#!/bin/sh
# Runs inside a fresh debian:trixie container. Mounts: /debs (built debs).
# Serves /debs as a local apt repository, installs tetronos-suite from it and
# checks every Depends of the metapackages is installed.
export DEBIAN_FRONTEND=noninteractive
fail=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; fail=1; }
installed() { dpkg-query -W -f '${db:Status-Abbrev} ${Package}\n' 2>/dev/null | awk '$1 == "ii" {print $2}' | sort; }

apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends apt-utils >/dev/null 2>&1 || { echo "FAIL apt-utils"; exit 1; }
mkdir -p /repo && cp /debs/*.deb /repo/
(cd /repo && apt-ftparchive packages . > Packages && apt-ftparchive release . > Release)
echo "deb [trusted=yes] file:/repo ./" > /etc/apt/sources.list.d/tetronos-local.list
apt-get update -qq >/dev/null

echo "== apt install tetronos-suite (local repo, no Recommends)"
if apt-get install -y -qq --no-install-recommends tetronos-suite >/tmp/apt.log 2>&1; then ok "apt install resolves Depends"
else bad "apt install"; tail -5 /tmp/apt.log; exit 1; fi

for meta in tetronos-core tetronos-suite; do
	echo "== Depends of $meta"
	for dep in $(dpkg-query -W -f '${Depends}' "$meta" | tr ',' '\n' | sed 's/(.*)//; s/|.*//; s/ //g'); do
		dpkg -s "$dep" 2>/dev/null | grep -q 'Status: install ok installed' && ok "$dep installed" || bad "$dep not installed"
	done
done

echo "== remove the metapackages"
before=$(installed)
apt-get remove -y -qq tetronos-suite tetronos-core >/dev/null 2>&1 && ok "apt remove" || bad "apt remove"
gone=$(echo "$before" | grep -vxF "$(installed)")
[ "$gone" = "$(printf 'tetronos-core\ntetronos-suite')" ] && ok "only the metapackages removed" || bad "also removed: $gone"
[ $fail = 0 ] && echo "ALL PASS" || echo "FAILURES"
exit $fail
