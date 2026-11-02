"""Run directly: python bot.py. This file does not execute on import."""
import os
import sys

from just_ai.config import ConfigError, ROOT, load_settings
from just_ai.runtime import StartupError, run, safe_logging


def main():
    os.umask(0o077)
    safe_logging()
    try:
        run(load_settings(), ROOT)
        return 0
    except (ConfigError, StartupError) as exc:
        print(str(exc))
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        # Intentionally no traceback or raw exception string: URLs may include tokens.
        print(f"Startup stopped ({type(exc).__name__}). Run: python doctor.py --live")
    return 1


if __name__ == "__main__":
    sys.exit(main())
