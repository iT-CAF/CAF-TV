# Sourced by find-tv.sh and setup.sh: sets SYS_PY (an array) to a Python 3.10-3.13 that really runs.
# Older ones can't load the cryptography wheel (macOS' system 3.9); newer ones have no wheels yet, so pip would
# have to build them. Preferred: python3.13, python3.12, Homebrew's python3, then any python3. On Windows
# `python`/`python3` can be the Microsoft Store shortcut that does nothing, and right after
# `winget install Python.Python.3.12` the terminal's PATH doesn't have the new Python yet, so its install
# folders are tried too, and the `py` launcher last.
py_ok() { "$@" -c "import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] < (3, 14)))" >/dev/null 2>&1; }
pick_python() {
  local c la v bad=
  local -a cands=(python3.13 python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3 python)
  if command -v cygpath >/dev/null 2>&1; then   # Git Bash on Windows
    la=$(cygpath -u "${LOCALAPPDATA:-}" 2>/dev/null || true)
    for c in "$la"/Programs/Python/Python3*/python.exe "/c/Program Files/Python3"*/python.exe; do
      [ -f "$c" ] && cands+=("$c")
    done
  fi
  for c in "${cands[@]}"; do
    if py_ok "$c"; then SYS_PY=("$c"); return 0; fi
    # a Python that runs but is outside 3.10-3.13: remember it, to say why it was passed over
    [ -n "$bad" ] || bad=$("$c" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null) || bad=
  done
  for c in "-3.13" "-3.12" "-3"; do
    if py_ok py "$c"; then SYS_PY=(py "$c"); return 0; fi
  done
  if [ -n "$bad" ]; then
    case "$bad" in
      3.[0-9]) v="too old: the ADB package's cryptography wheel won't load on it" ;;
      *)       v="too new: it has no wheels yet, so pip would have to build them" ;;
    esac
    echo "!! Python $bad is $v."
    echo "   Install Python 3.12 (macOS: brew install python@3.12; Windows: winget install -e --id"
    echo "   Python.Python.3.12), then run the same command again: it is found without a new terminal."
    return 1
  fi
  echo "!! No working Python 3 here. Install it (macOS: brew install python@3.12; Windows: winget install -e"
  echo "   --id Python.Python.3.12), then run the same command again: it is found without a new terminal."
  return 1
}
