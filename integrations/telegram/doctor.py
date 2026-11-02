"""Local checks by default. --live checks Telegram identity/webhook; no messages."""
import argparse
import asyncio
import sys
from importlib.metadata import version

from telegram import Bot
from just_ai.config import ROOT, ConfigError, load_settings
from just_ai.provider import Provider, ProviderError
from just_ai.runtime import safe_logging
from just_ai.store import Store


async def database_check():
    store = Store(ROOT / "data" / "workspace.sqlite3")
    try:
        await store.initialize()
        async with store.db.execute("PRAGMA quick_check") as cur:
            healthy = (await cur.fetchone())[0] == "ok"
        print("SQLite async startup/integrity: " + ("PASS" if healthy else "FAIL"))
        return healthy
    except Exception as exc:
        print(f"Database check failed ({type(exc).__name__}); details suppressed.")
        return False
    finally:
        await store.close()


async def remote(settings, check_ai):
    ok = True
    try:
        async with Bot(settings.token) as bot:
            me = await bot.get_me()
            print(f"Telegram identity: @{me.username}")
            if settings.expected_username and (me.username or "").lower() != settings.expected_username:
                print("FAIL: configured bot identity does not match.")
                ok = False
            info = await bot.get_webhook_info()
            print("Webhook: present (polling blocked)" if info.url else "Webhook: absent")
            ok = ok and not info.url
            print("This check does not establish whether another polling process is running.")
    except Exception as exc:
        print(f"Telegram check failed ({type(exc).__name__}); details suppressed.")
        ok = False
    if check_ai:
        provider = Provider(settings)
        try:
            await provider.answer("Reply only OK.", [{"role": "user", "content": "Connection check."}])
            print("AI text generation: PASS")
        except ProviderError as exc:
            print("AI check: " + str(exc))
            ok = False
        finally:
            await provider.close()
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Call Telegram getMe/getWebhookInfo only")
    parser.add_argument("--check-ai", action="store_true", help="Also send a small paid API request to the configured model")
    args = parser.parse_args()
    safe_logging()
    print("Python: " + sys.version.split()[0])
    for name in ("python-telegram-bot", "httpx", "python-dotenv", "aiosqlite"):
        print(name + ": " + version(name))
    if not asyncio.run(database_check()):
        return 1
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(str(exc))
        return 1
    print("Telegram token: configured (value hidden)")
    print("AI provider: " + settings.provider)
    print("AI key: " + ("configured" if settings.api_key else "missing"))
    print("AI model: " + ("configured" if settings.model else "missing"))
    print("Allowed users: " + str(len(settings.allowed)))
    print("AI usage limit per user/day: " + str(settings.daily_limit))
    if not settings.allowed:
        print("Setup mode: use /whoami in Telegram, then configure that user ID on the host.")
    if args.live or args.check_ai:
        return 0 if asyncio.run(remote(settings, args.check_ai)) else 1
    print("Local settings checked. Network connections have NOT been checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
