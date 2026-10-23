#!/usr/bin/env bash
# The whole setup in one command, made for slow or flaky ADB: every finished step is remembered, so after
# any failure just run it again and it carries on where it stopped.
#   optimize/run.sh            do the next steps
#   optimize/run.sh status     what is done
#   optimize/run.sh again      redo every step on the same TV, as after a TV system update put things back
#                              (the apps' settings stay: installing over keeps them; the old summary.md
#                              becomes summary-<n>.md so the new run's before/after starts clean)
#   SKIP_LAUNCHER=1 optimize/run.sh   keep the TV's own home screen (firmware that won't let another app be Home)
#   SKIP_EXTRAS=1 optimize/run.sh     without TV Bro and SmartTube
# Before: optimize/setup.sh and optimize/find-tv.sh. Optional packages the household gave up go in
# optimize/lists/mine.txt (one per line, picked from lists/tcl-optional.txt) before running.
# Results in optimize/run/: summary.md (before/after), ram-*.txt, backup.txt, report.md, steps.log (times), run.log.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-optimize/venv/bin/python}"
RUN=optimize/run
mkdir -p "$RUN"
tv() { "$PY" -I optimize/tv.py "$@"; }

STEPS=(probe backup keep before before-saver safe mine tweaks screensaver launcher extras after after-saver report)
title() {
  case "$1" in
    probe)       echo "Connect and identify the TV" ;;
    backup)      echo "Save the TV's current state" ;;
    keep)        echo "Turn protected features back on if anything turned them off" ;;
    before)      echo "Measure before (restart + 3 min)" ;;
    before-saver) echo "Measure the TV's own screensaver (1 min)" ;;
    safe)        echo "Disable telemetry, ads and demos (lists/tcl-safe.txt)" ;;
    mine)        echo "Disable the household's optional picks (lists/mine.txt)" ;;
    tweaks)      echo "Speed and memory tweaks" ;;
    screensaver) echo "Install شاشة كاف" ;;
    launcher)    echo "Install the home screen (safety switch on)" ;;
    extras)      echo "Install TV Bro (web browser) and SmartTube (YouTube without ads)" ;;
    after)       echo "Measure after (restart + 3 min)" ;;
    after-saver) echo "Measure our screensaver (1 min)" ;;
    report)      echo "Write the report" ;;
  esac
}

if [ "${1:-}" = again ]; then   # a TV system update can re-enable what we turned off and take Home back
  rm -f "$RUN"/.done-* "$RUN/steps.log"
  kept=
  if [ -f "$RUN/summary.md" ]; then   # measure.sh appends: a second run's before/after lines would double up
    n=1; while [ -e "$RUN/summary-$n.md" ]; do n=$((n + 1)); done
    mv "$RUN/summary.md" "$RUN/summary-$n.md"; kept=" The last run's summary.md is now summary-$n.md."
  fi
  echo "Marks cleared: every step runs again (the backup from the first run is kept).$kept"
  shift
fi
if [ "${1:-}" = status ]; then
  for s in "${STEPS[@]}"; do printf '%s %s\n' "$([ -f "$RUN/.done-$s" ] && echo '✓' || echo '·')" "$(title "$s")"; done
  if [ -f "$RUN/report.md" ]; then   # the report's !! lines, so nobody has to grep it by hand
    grep '!!' "$RUN/report.md" | sed 's/^/report: /' || echo "report: no !! lines"
  fi
  exit 0
fi

exec > >(tee -a "$RUN/run.log") 2>&1   # everything it says, for optimize/share.sh: its !! lines and dropped connections

check_list() {   # never disable what UAD-ng rates Unsafe; show everything that is not "Recommended"
  local out
  out=$("$PY" -I optimize/check-packages.py "$1")
  echo "$out" | grep -v '^Recommended' | sed 's/^/   /' || true
  if echo "$out" | grep -q '^Unsafe'; then echo "!! $1 has a package rated Unsafe. Take it out and run again."; exit 1; fi
}

report() {
  echo "# TV setup report — $(date '+%Y-%m-%d %H:%M')"
  echo
  grep -E 'model|version.release|display.id' "$RUN/tv.txt" || true
  echo
  cat "$RUN/summary.md"
  echo
  echo "Features that must stay on:"
  for p in com.tcl.airplay2 com.google.android.apps.mediashell com.tcl.miracast com.google.android.katniss \
           com.tcl.tvinput com.android.vending com.google.android.gms; do
    if tv "pm list packages -d $p" | grep -qx "package:$p"; then echo "- !! $p is DISABLED"
    elif tv "pm list packages $p" | grep -qx "package:$p"; then echo "- ok: $p"
    fi
  done
  echo
  echo "Home: $(tv "cmd package resolve-activity --brief -c android.intent.category.HOME -a android.intent.action.MAIN" | tail -1)"
  echo "Screensaver: $(tv "settings get secure screensaver_components")"
  echo "Versions: screensaver $(tv "dumpsys package sa.urtv.screensaver | grep -m1 versionName" | sed 's/.*=//'), home $(tv "dumpsys package sa.urtv.home | grep -m1 versionName" | sed 's/.*=//')"
  echo "Extras: TV Bro $([ -n "$(tv "pm list packages com.phlox.tvwebbrowser")" ] && echo yes || echo no), SmartTube $([ -n "$(tv "pm list packages org.smarttube.stable")" ] && echo yes || echo no)"
  local picks
  picks=$(grep -cvE '^\s*(#|$)' optimize/lists/mine.txt 2>/dev/null || true)
  echo "Optional picks (lists/mine.txt): ${picks:-0}"
  echo
  echo "Packages from our lists (off: disabled, on: still on, absent: not on this TV):"
  local disabled installed l pkg state
  disabled=$(tv "pm list packages -d" | tr -d '\r')
  installed=$(tv "pm list packages" | tr -d '\r')
  for l in tcl-safe tcl-optional keep home-replaced; do
    for pkg in $(grep -vE '^\s*(#|$)' "optimize/lists/$l.txt" | awk '{print $1}'); do
      if grep -qx "package:$pkg" <<< "$disabled"; then state=off
      elif grep -qx "package:$pkg" <<< "$installed"; then state=on
      else state=absent; fi
      echo "- pkg $state: $pkg ($l)"
    done
  done
  echo "Left off the home screen:"
  optimize/dock.sh hidden 2> /dev/null | sed 's/^/- home hides: /' || true
  echo "Undo everything: optimize/reset.sh"
}

do_step() {
  case "$1" in
    probe)       tv --probe | tee "$RUN/tv.txt" ;;
    backup)      optimize/backup.sh && cp "$(ls -t optimize/backup-*.txt | head -1)" "$RUN/backup.txt" ;;
    keep)        optimize/keep.sh | tee "$RUN/keep.txt" ;;
    before)      optimize/measure.sh before ;;
    before-saver) optimize/measure.sh before-screensaver --screensaver ;;
    safe)        check_list optimize/lists/tcl-safe.txt
                 optimize/disable.sh optimize/lists/tcl-safe.txt > /dev/null ;;
    mine)        if [ -s optimize/lists/mine.txt ]; then
                   check_list optimize/lists/mine.txt
                   optimize/disable.sh optimize/lists/mine.txt > /dev/null
                 else
                   echo "   (no lists/mine.txt: nothing optional)"
                 fi ;;
    tweaks)      optimize/tweaks.sh apply ;;
    screensaver) optimize/install.sh saver ;;
    launcher)    if [ "${SKIP_LAUNCHER:-}" = 1 ]; then echo "   skipped (SKIP_LAUNCHER=1): the TV keeps its own home screen"
                 else optimize/install.sh launcher; fi ;;
    extras)      if [ "${SKIP_EXTRAS:-}" = 1 ]; then echo "   skipped (SKIP_EXTRAS=1)"; else optimize/install.sh extras; fi ;;
    after)       optimize/measure.sh after ;;
    after-saver) optimize/measure.sh after-screensaver --screensaver ;;
    report)      report > "$RUN/report.md"; cat "$RUN/report.md" ;;
  esac
}

# The .done-* marks belong to one TV: a different one (its serial, else its address) starts from the top.
tv_id=$(tv "getprop ro.serialno" 2> /dev/null | tr -d '\r\n ' || true)
[ -n "$tv_id" ] || tv_id="${TV_HOST:-$(cat optimize/.tv_host 2> /dev/null || true)}"
if [ -n "$tv_id" ] && [ "$(cat "$RUN/.tv" 2> /dev/null || true)" != "$tv_id" ]; then
  [ -f "$RUN/.tv" ] && echo "A different TV than the last run: starting from the first step."
  rm -f "$RUN"/.done-* "$RUN/steps.log"
  echo "$tv_id" > "$RUN/.tv"
fi

# when each step started, ended or stopped: optimize/share.sh turns it into how long each took
stamp() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$RUN/steps.log"; }
trap 'rc=$?; [ "$rc" -eq 0 ] || stamp "stopped ${current:-?} (exit $rc)"' EXIT
for s in "${STEPS[@]}"; do
  [ -f "$RUN/.done-$s" ] && continue
  current=$s
  echo
  echo "▶ $(title "$s")"
  stamp "start $s"
  do_step "$s"
  touch "$RUN/.done-$s"
  stamp "done $s"
done
if grep -q '!!' "$RUN/report.md"; then
  current=report-check   # the stop below is no step's fault
  echo
  echo "Done, with problems:"
  grep '!!' "$RUN/report.md"
  rm -f "$RUN/.done-report"   # the next run writes the report again, so a fixed problem stops showing
  exit 1
fi
echo
echo "All steps done. Next: settings (optimize/saver.sh), favourites (optimize/dock.sh), photos (optimize/shot.sh)."
