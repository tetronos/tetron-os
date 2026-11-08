#!/bin/sh
# Runs inside a fresh debian:trixie container. Mounts: /debs (this build), /prev (the
# previous release's attached packages). Installs the editions from the previous release,
# upgrades to this build with apt full-upgrade and checks that no package was removed and
# every package of the previous release is at this build's version (packaging/manifest.toml rules).
export DEBIAN_FRONTEND=noninteractive
fail=0
ok()  { echo "  ok   $*"; }
bad() { echo "  FAIL $*"; fail=1; }
installed() { dpkg-query -W -f '${db:Status-Abbrev} ${Package}\n' 2>/dev/null | awk '$1 == "ii" {print $2}' | sort; }
repo() { # repo DIR...: serve the debs in DIR... as the local apt repository
	rm -rf /repo && mkdir -p /repo && cp "$@" /repo/
	(cd /repo && apt-ftparchive packages . > Packages && apt-ftparchive release . > Release)
	apt-get update -qq >/dev/null
}

echo "deb http://deb.debian.org/debian trixie-backports main" > /etc/apt/sources.list.d/backports.list
cp /kmscon-backports.pref /etc/apt/preferences.d/kmscon-backports.pref
sed -i 's/^Components: main$/Components: main non-free-firmware/' /etc/apt/sources.list.d/debian.sources
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends apt-utils >/dev/null 2>&1 || { echo "FAIL apt-utils"; exit 1; }
echo "deb [trusted=yes] file:/repo ./" > /etc/apt/sources.list.d/tetronos-local.list
# The previous release installs tetronos-apt-source, which adds the live tetronos repo:
# keep it out, so only the previous release and this build are compared.
printf 'Package: *\nPin: origin tetronos.github.io\nPin-Priority: -1\n' > /etc/apt/preferences.d/no-live-tetronos.pref

# The previous release: its own packages, plus this build's copies of other repos' debs.
prev_names=$(for f in /prev/*.deb; do dpkg-deb -f "$f" Package; done | sort -u)
mkdir -p /prevrepo && cp /prev/*.deb /prevrepo/
for f in /debs/*.deb; do echo "$prev_names" | grep -qxF "$(dpkg-deb -f "$f" Package)" || cp "$f" /prevrepo/; done
repo /prevrepo/*.deb
echo "== install the previous release ($(ls /prev/*.deb | wc -l) packages)"
if apt-get install -y -qq --no-install-recommends tetronos-suite tetronos-desktop >/tmp/apt.log 2>&1; then ok "previous release installs"
else bad "previous release install"; tail -5 /tmp/apt.log; exit 1; fi
before=$(installed)

echo "== apt full-upgrade to this build"
repo /debs/*.deb
if apt-get full-upgrade -y -qq --no-install-recommends >/tmp/up.log 2>&1; then ok "full-upgrade"
else bad "full-upgrade"; tail -5 /tmp/up.log; fi
removed=$(echo "$before" | grep -vxF "$(installed)")
[ -z "$removed" ] && ok "no package removed" || bad "removed: $(echo $removed)"
while IFS='|' read -r name ver _; do
	echo "$before" | grep -qxF "$name" || continue
	echo "$prev_names" | grep -qxF "$name" || continue  # other repos' debs: any newer one is fine
	got=$(dpkg-query -W -f '${Version}' "$name" 2>/dev/null)
	[ "$got" = "$ver" ] && ok "$name $ver" || bad "$name at ${got:-nothing}, this build has $ver"
done < /debs/tests.list
[ $fail = 0 ] && echo "ALL PASS" || echo "FAILURES"
exit $fail
