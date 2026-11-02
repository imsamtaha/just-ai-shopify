#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
umask 077
exec .venv/bin/python bot.py
