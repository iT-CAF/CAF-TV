#!/usr/bin/env bash
# Turn back on anything from optimize/lists/keep.txt that is disabled (AirPlay, casting, mirroring, voice, remote,
# inputs, tuner, firmware updates, Play Store, Google services). Our scripts never disable these, but a TV
# optimized before, by other tools or older versions, may have them off. Safe to run any time.
#   optimize/keep.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-optimize/venv/bin/python}"
off=$("$PY" -I optimize/tv.py "pm list packages -d" | sed -n 's/^package://p' | tr -d '\r' \
      | grep -Fxf <(grep -vE '^\s*(#|$)' optimize/lists/keep.txt | awk '{print $1}') || true)
# the stock home and setup app are in keep.txt but belong to install.sh launcher: leave them to it
off=$(printf '%s\n' "$off" | grep -vxE 'com.google.android.apps.tv.launcherx|com.google.android.tvlauncher|com.google.android.tungsten.setupwraith|com.tcl.keycustomfunctionservice' || true)
if [ -z "$off" ]; then echo "Protected features: all on."; exit 0; fi
echo "Turning back on (they must never be off):"
printf '%s\n' "$off" | sed 's/^/   /'
printf '%s\n' "$off" | awk '{print "pm enable " $1}' | "$PY" -I optimize/tv.py --batch > /dev/null
disabled() { "$PY" -I optimize/tv.py "pm list packages -d" | sed -n 's/^package://p' | tr -d '\r' | grep -Fxf <(printf '%s\n' "$off") || true; }
still=$(disabled)
if [ -n "$still" ]; then   # a second try, the way Android 9 sets want it
  printf '%s\n' "$still" | awk '{print "pm enable --user 0 " $1}' | "$PY" -I optimize/tv.py --batch > /dev/null || true
  still=$(disabled)
fi
if [ -n "$still" ]; then
  # Some packages the TV itself keeps off and pm enable can't turn on (a TCL outside Alexa's regions ships
  # com.tcl.smartalexa disabled, issue #4). That is not our doing: say so and go on. Only a package that was on
  # before this run (optimize/run/backup.txt) and is off now is a problem to stop for.
  before=$(awk '/^== disabled packages/{s=1; next} /^== /{s=0} s' optimize/run/backup.txt 2> /dev/null \
           | sed -n 's/^package://p' | tr -d '\r' || true)
  ours=$(grep -Fxvf <(printf '%s\n' "$before") <<< "$still" || true)
  [ -f optimize/run/backup.txt ] || ours=
  kept=$(grep -Fxvf <(printf '%s\n' "${ours:-}") <<< "$still" || true)
  [ -z "$kept" ] || echo "   left off by the TV itself (off before CAF TV, and pm enable can't turn it on): $(paste -sd' ' <<< "$kept")"
  if [ -n "$ours" ]; then echo "!! still off, tell the person: $(paste -sd' ' <<< "$ours")"; exit 1; fi
fi
echo "Protected features: all on."
