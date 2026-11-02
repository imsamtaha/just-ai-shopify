"""Async SQLite persistence with serialized transactions and scoped chat memory."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.db = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with self._lock:
            if self.db is not None:
                return
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            db = await aiosqlite.connect(self.path, timeout=10)
            try:
                db.row_factory = aiosqlite.Row
                await db.execute("PRAGMA secure_delete=ON")
                await db.execute("PRAGMA busy_timeout=10000")
                await db.executescript("""
                    CREATE TABLE IF NOT EXISTS preferences (
                        user_id INTEGER PRIMARY KEY, mode TEXT DEFAULT 'general',
                        skin TEXT DEFAULT 'classic', language TEXT DEFAULT 'auto');
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, content TEXT,
                        chat_id INTEGER);
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT,
                        content TEXT, done INTEGER DEFAULT 0, created TEXT DEFAULT CURRENT_TIMESTAMP);
                    CREATE INDEX IF NOT EXISTS item_user ON items(user_id, kind);
                    CREATE TABLE IF NOT EXISTS usage (
                        user_id INTEGER, day TEXT, count INTEGER DEFAULT 0,
                        PRIMARY KEY(user_id, day));
                    CREATE TABLE IF NOT EXISTS shop_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                        action TEXT NOT NULL, resource TEXT NOT NULL, status TEXT NOT NULL,
                        created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                    CREATE INDEX IF NOT EXISTS shop_audit_resource ON shop_audit(resource,status);
                """)
                async with db.execute("PRAGMA table_info(messages)") as cursor:
                    columns = {row[1] for row in await cursor.fetchall()}
                # Previous releases allowed private chats only: chat ID = user ID.
                if "chat_id" not in columns:
                    await db.execute("ALTER TABLE messages ADD COLUMN chat_id INTEGER")
                await db.execute("UPDATE messages SET chat_id=user_id WHERE chat_id IS NULL")
                await db.execute("CREATE INDEX IF NOT EXISTS message_chat_user ON messages(chat_id,user_id,id)")
                await db.commit()
                self.path.chmod(0o600)
            except BaseException:
                await db.close()
                raise
            self.db = db

    async def close(self):
        async with self._lock:
            if self.db is not None:
                await self.db.close()
                self.db = None

    @asynccontextmanager
    async def _transaction(self):
        async with self._lock:
            if self.db is None:
                raise RuntimeError("Database has not been initialized")
            await self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
                await self.db.commit()
            except BaseException:
                await self.db.rollback()
                raise

    async def prefs(self, uid):
        async with self._transaction() as db:
            await db.execute("INSERT OR IGNORE INTO preferences(user_id) VALUES (?)", (uid,))
            async with db.execute("SELECT * FROM preferences WHERE user_id=?", (uid,)) as cur:
                return dict(await cur.fetchone())

    async def preference(self, uid, field, value):
        from .catalog import SKILLS, SKINS
        choices = {"mode": SKILLS, "skin": SKINS, "language": ("auto", "en", "ar")}
        if field not in choices or value not in choices[field]:
            raise ValueError("Unknown preference")
        async with self._transaction() as db:
            await db.execute("INSERT OR IGNORE INTO preferences(user_id) VALUES (?)", (uid,))
            await db.execute(f"UPDATE preferences SET {field}=? WHERE user_id=?", (value, uid))

    async def history(self, uid, chat_id=None):
        chat_id = uid if chat_id is None else chat_id
        async with self._transaction() as db:
            async with db.execute(
                "SELECT role,content FROM messages WHERE user_id=? AND chat_id=? ORDER BY id", (uid, chat_id)
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def exchange(self, uid, question, answer, chat_id=None):
        chat_id = uid if chat_id is None else chat_id
        async with self._transaction() as db:
            await db.executemany("INSERT INTO messages(user_id,chat_id,role,content) VALUES (?,?,?,?)",
                                 [(uid, chat_id, "user", question), (uid, chat_id, "assistant", answer)])
            await db.execute("""DELETE FROM messages WHERE user_id=? AND chat_id=? AND id NOT IN
                (SELECT id FROM messages WHERE user_id=? AND chat_id=? ORDER BY id DESC LIMIT 12)""",
                (uid, chat_id, uid, chat_id))

    async def reset(self, uid, chat_id=None):
        chat_id = uid if chat_id is None else chat_id
        async with self._transaction() as db:
            await db.execute("DELETE FROM messages WHERE user_id=? AND chat_id=?", (uid, chat_id))

    async def add(self, uid, kind, content):
        if kind not in ("note", "task") or not content.strip() or len(content) > 2000:
            raise ValueError("Use 1–2000 characters.")
        async with self._transaction() as db:
            async with db.execute("SELECT count(*) FROM items WHERE user_id=? AND kind=?", (uid, kind)) as cur:
                count = (await cur.fetchone())[0]
            if count >= 100:
                raise ValueError("Limit reached: 100 items per type. Delete an item first.")
            async with db.execute("INSERT INTO items(user_id,kind,content) VALUES (?,?,?)", (uid, kind, content)) as cur:
                return cur.lastrowid

    async def items(self, uid, kind):
        async with self._transaction() as db:
            async with db.execute(
                "SELECT * FROM items WHERE user_id=? AND kind=? ORDER BY id DESC", (uid, kind)
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def change_item(self, uid, kind, item_id, complete=False):
        async with self._transaction() as db:
            if complete:
                sql = "UPDATE items SET done=1 WHERE user_id=? AND kind=? AND kind='task' AND id=?"
            else:
                sql = "DELETE FROM items WHERE user_id=? AND kind=? AND id=?"
            async with db.execute(sql, (uid, kind, item_id)) as cur:
                return cur.rowcount > 0

    async def used(self, uid, day=None):
        day = day or datetime.now(timezone.utc).date().isoformat()
        async with self._transaction() as db:
            async with db.execute("SELECT count FROM usage WHERE user_id=? AND day=?", (uid, day)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def reserve(self, uid, limit, day=None):
        day = day or datetime.now(timezone.utc).date().isoformat()
        async with self._transaction() as db:
            await db.execute("DELETE FROM usage WHERE day < ?", (day,))
            await db.execute("INSERT OR IGNORE INTO usage(user_id,day) VALUES (?,?)", (uid, day))
            async with db.execute(
                "UPDATE usage SET count=count+1 WHERE user_id=? AND day=? AND count < ?", (uid, day, limit)
            ) as cur:
                return bool(cur.rowcount)

    async def forget(self, uid):
        # Retain today's counter so deletion cannot bypass the spending limit.
        async with self._transaction() as db:
            for table in ("preferences", "messages", "items"):
                await db.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))

    async def shop_start(self, uid, action, resource):
        async with self._transaction() as db:
            async with db.execute("SELECT id FROM shop_audit WHERE resource=? AND status IN ('started','unknown','verification_failed')", (resource,)) as cur:
                if await cur.fetchone():
                    raise RuntimeError("Unresolved store operation")
            async with db.execute("INSERT INTO shop_audit(user_id,action,resource,status) VALUES (?,?,?,'started')", (uid, action, resource)) as cur:
                return cur.lastrowid

    async def shop_finish(self, entry_id, status):
        if status not in ("verified", "rejected", "unknown", "verification_failed", "reviewed"):
            raise ValueError("Invalid audit status")
        async with self._transaction() as db:
            await db.execute("UPDATE shop_audit SET status=? WHERE id=?", (status, entry_id))

    async def shop_history(self):
        async with self._transaction() as db:
            async with db.execute("SELECT * FROM shop_audit ORDER BY id DESC LIMIT 15") as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def shop_entry(self, entry_id):
        async with self._transaction() as db:
            async with db.execute("SELECT * FROM shop_audit WHERE id=?", (entry_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def shop_unresolved(self, resource):
        async with self._transaction() as db:
            async with db.execute("SELECT 1 FROM shop_audit WHERE resource=? AND status IN ('started','unknown','verification_failed') LIMIT 1", (resource,)) as cur:
                return bool(await cur.fetchone())
