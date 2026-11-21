# Start tetron-wm in a login shell on the primary console. kmscon runs the
# login on a pts, so the console is found by walking up to a kmscon process;
# a raw tty1 also counts. Never over ssh, never inside tetron-wm.
if [ -z "$TETRON_WM_ACTIVE" ] && [ -z "$SSH_CONNECTION" ] && [ -x /usr/bin/tetron-session ]; then
	_tw=0
	[ "$(tty)" = /dev/tty1 ] && _tw=1
	_p=$PPID
	while [ "$_tw" = 0 ] && [ "${_p:-0}" -gt 1 ]; do
		[ "$(cat /proc/$_p/comm 2>/dev/null)" = kmscon ] && _tw=1
		_p=$(awk '/^PPid:/{print $2}' /proc/$_p/status 2>/dev/null)
	done
	[ "$_tw" = 1 ] && { unset _tw _p; exec /usr/bin/tetron-session; }
	unset _tw _p
fi
