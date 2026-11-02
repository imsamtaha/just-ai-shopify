"""Interactive setup, Telegram preflight, then foreground bot activation."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from just_ai.config import ConfigError, load_settings

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configure", action="store_true", help="Edit saved settings before starting")
    args = parser.parse_args()
    os.chdir(ROOT)
    needs_setup = args.configure
    try:
        load_settings()
    except ConfigError:
        needs_setup = True
    if needs_setup:
        print("Secure setup is required. Enter secrets only in this terminal.", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / "configure.py")])
        if result.returncode:
            print("Setup did not finish. No bot was started.")
            return result.returncode
    print("Checking Telegram identity and webhook before starting...", flush=True)
    result = subprocess.run([sys.executable, str(ROOT / "doctor.py"), "--live"])
    if result.returncode:
        print("Activation stopped. Resolve the check above and run this command again.")
        print("To correct credentials or the username: python activate.py --configure")
        return result.returncode
    settings = load_settings()
    if not settings.allowed:
        print("Setup mode: send /whoami to your bot, then press Ctrl+C here.")
        print("Run activate.py --configure again and enter your personal numeric user ID.")
    if not settings.ai_ready:
        print("AI chat needs a key and model for the selected provider. Notes and tasks do not.")
    print("Starting the bot. Keep this computer awake and this terminal open. Ctrl+C stops it.", flush=True)
    return subprocess.run([sys.executable, str(ROOT / "bot.py")]).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nActivation stopped.")
        sys.exit(130)
    except Exception as exc:
        print(f"Activation failed ({type(exc).__name__}); details hidden to protect credentials.")
        sys.exit(1)
