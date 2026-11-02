"""Runtime startup, minimal logging, and a process-lifetime file lock."""
import asyncio
import logging
import os
from contextlib import contextmanager
from pathlib import Path

from telegram import BotCommand, BotCommandScopeAllPrivateChats
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from .catalog import COMMANDS
from .handlers import Handlers
from .provider import Provider
from .store import Store
from .shopify_config import load_shopify_settings


class StartupError(Exception):
    pass


def safe_logging():
    logging.basicConfig(level=logging.CRITICAL, format="%(levelname)s: %(message)s", force=True)
    logging.getLogger("just_ai").setLevel(logging.INFO)
    for name in ("httpx", "httpcore", "telegram", "asyncio"):
        logging.getLogger(name).setLevel(logging.CRITICAL)


@contextmanager
def instance_lock(path):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stream = path.open("a+b", buffering=0)
    locked = False
    try:
        if stream.seek(0, 2) == 0:
            stream.write(b"0")
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            raise StartupError("This package is already running in another process.") from None
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def build_application(settings, store, provider, request=None, shopify_settings=None):
    handlers = Handlers(settings, store, provider, shopify_settings)

    async def startup(app):
        await store.initialize()
        user = await app.bot.get_me()
        if settings.expected_username and (user.username or "").lower() != settings.expected_username:
            raise StartupError("Bot identity mismatch. Check EXPECTED_BOT_USERNAME on the host.")
        info = await app.bot.get_webhook_info()
        if info.url:
            raise StartupError("An existing webhook is configured. Review the current deployment before switching to polling.")
        scope = BotCommandScopeAllPrivateChats()
        await app.bot.set_my_commands([BotCommand(cmd, en) for cmd, en, ar in COMMANDS], scope=scope)
        await app.bot.set_my_commands([BotCommand(cmd, ar) for cmd, en, ar in COMMANDS], scope=scope, language_code="ar")
        logging.getLogger("just_ai").info("Telegram identity verified: @%s. Starting polling.", user.username)
        if not settings.allowed:
            logging.getLogger("just_ai").info("Setup mode: only /whoami and /privacy are available. Configure ALLOWED_USER_IDS.")

    async def shutdown(app):
        await handlers.shopify.close()
        await provider.close()
        await store.close()

    builder = (Application.builder().token(settings.token).concurrent_updates(False)
               .post_init(startup).post_shutdown(shutdown))
    if request is not None:
        builder = builder.request(request).get_updates_request(request)
    app = builder.build()
    app.bot_data["shopify_controls"] = handlers.shopify
    app.add_handler(CommandHandler([cmd for cmd, _, _ in COMMANDS], handlers.command))
    app.add_handler(CallbackQueryHandler(handlers.callback))
    app.add_handler(MessageHandler(filters.COMMAND, handlers.command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text))
    app.add_handler(MessageHandler(filters.ALL, handlers.unsupported))
    app.add_error_handler(handlers.error)
    return app


def run(settings, root):
    data = root / "data"
    with instance_lock(data / "bot.lock"), asyncio.Runner() as runner:
        loop = runner.get_loop()
        store = Store(data / "workspace.sqlite3")
        provider = Provider(settings)
        app = None
        try:
            app = build_application(settings, store, provider, shopify_settings=load_shopify_settings(root))
            # Keep queued updates; guard ignores commands older than five minutes.
            app.run_polling(allowed_updates=["message", "callback_query"],
                            drop_pending_updates=False, bootstrap_retries=0, close_loop=False)
        finally:
            # Also close resources if initialization fails before post_shutdown.
            if app is not None:
                loop.run_until_complete(app.bot_data["shopify_controls"].close())
            loop.run_until_complete(provider.close())
            loop.run_until_complete(store.close())
