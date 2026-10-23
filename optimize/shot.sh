#!/usr/bin/env bash
# Screenshots without navigating by hand. Saves full-size PNGs in optimize/run/shots/<NAME>.png, and next to
# each a <NAME>-small.png, 960 px wide: the full ones are too large for some agents to attach (needs Pillow,
# which setup.sh installs; without it the small copy is skipped).
#   optimize/shot.sh home [NAME]          the home screen (after Home, 8 s)
#   optimize/shot.sh screensaver [NAME]   the screensaver (started now, 40 s for its data), then Back; where
#                                         Android won't start it over ADB, our app's preview of the same page
#   optimize/shot.sh favourites [NAME]    «ترتيب المفضلة»
#   optimize/shot.sh settings [NAME]      شاشة كاف's settings
#   optimize/shot.sh now NAME             whatever is on screen now
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-optimize/venv/bin/python}"
mkdir -p optimize/run/shots
tv() { "$PY" -I optimize/tv.py "$@" > /dev/null; }
case "${1:-}" in
  home)        tv "input keyevent KEYCODE_HOME"; sleep 8; name=home ;;
  screensaver) how=$(optimize/start-saver.sh --preview); echo "screensaver: $how"; sleep 34; name=screensaver ;;
  favourites)  tv "am start -n sa.urtv.home/.DockActivity"; sleep 4; name=favourites ;;
  settings)    tv "am start -n sa.urtv.screensaver/.SettingsActivity"; sleep 4; name=settings ;;
  now)         name="${2:?usage: optimize/shot.sh now NAME}" ;;
  *) sed -n '2,10p' "$0"; exit 1 ;;
esac
file="optimize/run/shots/${2:-$name}.png"
"$PY" -I optimize/tv.py --shot "$file"
[ "$1" = screensaver ] && tv "input keyevent KEYCODE_BACK"
small="${file%.png}-small.png"
if ! "$PY" -I -c 'import sys; from PIL import Image
im = Image.open(sys.argv[1]).convert("RGB"); w = 960
im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS).save(sys.argv[2], optimize=True)' "$file" "$small" 2> /dev/null; then
  echo "(no small copy: Pillow is missing, run optimize/setup.sh)"
  small=
fi
echo "$file"
[ -z "$small" ] || echo "$small"
