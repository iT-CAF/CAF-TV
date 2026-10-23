#!/usr/bin/env bash
# One-time setup: the pure-Python ADB client (no adb binary needed, works where macOS blocks adb).
# The APKs are built by GitHub Actions, so no Android SDK is needed here. Windows: run it in Git Bash.
# Adapted from github.com/mihirgupta0900/tv-home (MIT).
set -euo pipefail
cd "$(dirname "$0")"
. ./python.sh
pick_python || exit 1
"${SYS_PY[@]}" -m venv venv
if [ ! -e venv/bin/python ] && [ -e venv/Scripts/python.exe ]; then
  # Windows puts it in venv\Scripts: every script calls optimize/venv/bin/python, so point that there
  mkdir -p venv/bin
  printf '#!/usr/bin/env bash\nexec "$(dirname "$0")/../Scripts/python.exe" "$@"\n' > venv/bin/python
  chmod +x venv/bin/python
fi
if ! venv/bin/python -m pip install -q --no-cache-dir -r requirements.txt; then
  echo "!! Couldn't install the Python packages into optimize/venv (pip's error is above). If it is a network"
  echo "   error, allow this terminal network access (pypi.org), then run optimize/setup.sh again."
  exit 1
fi
# every `venv/bin/python -I` call verifies TLS with certifi (python.org's macOS Python ships no CA certificates)
for sp in venv/lib/python3.*/site-packages venv/Lib/site-packages; do
  [ -d "$sp" ] || continue
  printf '%s\n' 'import os' 'try:' '    import certifi' '    os.environ.setdefault("SSL_CERT_FILE", certifi.where())' \
    'except ImportError:' '    pass' > "$sp/sitecustomize.py"
done
# pip said yes: make sure tv.py will really start (keygen loads cryptography's DLL, which plain adb_shell doesn't)
if ! err=$(venv/bin/python -c "import adb_shell.adb_device, adb_shell.auth.keygen, adb_shell.auth.sign_pythonrsa" 2>&1); then
  echo "$err" | tail -1
  if grep -qi "too long" <<< "$err"; then
    echo "!! This folder's path is too long for Windows (over 260 characters inside optimize/venv). Clone CAF TV into"
    echo "   a short folder, such as C:\CAF TV: git clone -c core.longpaths=true https://github.com/DHME1/CAF-TV C:/CAF TV"
  else
    echo "!! The ADB package doesn't load from optimize/venv. Delete the folder optimize/venv, then run"
    echo "   optimize/setup.sh again."
  fi
  exit 1
fi
echo "✓ Python ADB client in optimize/venv"
# an HTTP error status still means the TLS handshake verified; only a certificate or network error fails
if venv/bin/python -I -c 'import urllib.request as u, urllib.error as e
try: u.urlopen("https://github.com", timeout=15)
except e.HTTPError: pass' 2>/dev/null; then
  echo "✓ TLS certificates"
else
  echo "!! This computer can't open https://github.com from optimize/venv (certificates or network). Check that it"
  echo "   is online, delete the folder optimize/venv, then run optimize/setup.sh again."
fi
