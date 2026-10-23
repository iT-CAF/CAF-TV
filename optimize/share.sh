#!/usr/bin/env bash
# How the setup went, for the TV's owner to send to CAF TV's author if they want to: the TV model and Android
# version, how long each step took and where it stopped, memory before and after, the protected-features check,
# and the agent's notes. Nothing personal (no city, clubs, apps, names, network addresses or paths).
#   optimize/share.sh "what went wrong, how long it cost, how it was fixed"
# Writes optimize/run/share.md and sends it to the author's Google Form (anonymous, no account). If it can't, a QR
# code takes it to the phone: docs/share/ (GitHub Pages) shows it with a button that sends it.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-optimize/venv/bin/python}"
"$PY" -c "import segno" 2> /dev/null || "$PY" -m pip install -q segno || true   # the QR code (older setups)
"$PY" -I optimize/share.py "$@"
