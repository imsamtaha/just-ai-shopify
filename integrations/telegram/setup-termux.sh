#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
umask 077
if ! command -v python >/dev/null 2>&1; then
  printf '%s\n' 'Python is missing. Run: pkg install python'
  exit 1
fi
if [ ! -e .venv ]; then
  python -m venv .venv
fi
if [ ! -x .venv/bin/python ]; then
  printf '%s\n' '.venv is not a working Termux environment. Inspect it before proceeding.'
  exit 1
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -q
printf '%s\n' 'Installed. Next: .venv/bin/python configure.py'
