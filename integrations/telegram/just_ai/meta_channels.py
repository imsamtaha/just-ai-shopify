"""Verified inbound messages and replies for WhatsApp Cloud API and Messenger."""
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
import math
import re
import sqlite3
import time

import httpx
from . import atlas
from .provider import Provider, ProviderError

HELP = ("ATLAS INTELLIGENCE — by JUST AI\n"
        "/atlas — project guide\n/training — recorded training reports\n"
        "/sessions — recent evaluations\n/strategies — strategy references\n"
        "/whoami — your channel ID\n/privacy — data use\n"
        "Ask /atlas <question> when AI is configured.\n"
        "مصادر أطلس وتقارير التدريب والاستراتيجيات؛ لا تنفيذ صفقات.")
PRIVACY = ("Messages pass through Meta. Allowed users' AI questions may include local ATLAS "
           "documentation and sanitized reports sent to the configured AI provider. "
           "No cross-channel chat history is shared. Pending messages are stored locally until "
           "processed; completed message text is cleared. Sender IDs, message IDs and delivery "
           "state are retained for up to seven days for duplicate prevention and limits. "
           "No trading orders or training jobs are executed.")


def valid_signature(body, signature, secret):
    if not secret or not isinstance(signature, str):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), signature.encode())


@dataclass(frozen=True)
class Incoming:
    channel: str
    message_id: str
    sender: str
    text: str
    timestamp: float


def incoming(payload, config, now=None):
    """Accept only the configured Page/phone, recent text and non-echo events."""
    now = time.time() if now is None else now
    events = []
    def add(channel, mid, sender, text, timestamp, divisor=1):
        try:
            stamp = float(timestamp) / divisor
        except (ValueError, TypeError):
            return
        if (not isinstance(mid, str) or not 1 <= len(mid) <= 256 or
                not isinstance(sender, str) or not re.fullmatch(r"[0-9]{1,30}", sender) or
                not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000 or
                not math.isfinite(stamp) or not -60 <= now - stamp <= 300):
            return
        events.append(Incoming(channel, mid, sender, text.strip(), stamp))
    if not isinstance(payload, dict) or not isinstance(payload.get("entry", []), list):
        raise ValueError("Invalid webhook envelope")
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        if payload.get("object") == "whatsapp_business_account" and config.enabled("whatsapp"):
            for change in entry.get("changes", []):
                if not isinstance(change, dict) or change.get("field") != "messages":
                    continue
                value = change.get("value", {})
                if value.get("metadata", {}).get("phone_number_id") != config.phone_id:
                    continue
                for message in value.get("messages", []):
                    if message.get("type") == "text":
                        add("whatsapp", message.get("id"), message.get("from"),
                            message.get("text", {}).get("body"), message.get("timestamp"))
        elif payload.get("object") == "page" and config.enabled("messenger") and entry.get("id") == config.page_id:
            for event in entry.get("messaging", []):
                message = event.get("message", {})
                if message.get("is_echo") or event.get("recipient", {}).get("id") != config.page_id:
                    continue
                add("messenger", message.get("mid"), event.get("sender", {}).get("id"),
                    message.get("text"), event.get("timestamp"), 1000)
    if len(events) > 100:
        raise ValueError("Too many messages")
    return events


class Inbox:
    """Durable deduplication; interrupted sends are never automatically retried."""
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS inbox (channel TEXT, mid TEXT, sender TEXT, "
                       "text TEXT, stamp REAL, state TEXT, created REAL, PRIMARY KEY(channel, mid))")
            db.execute("CREATE INDEX IF NOT EXISTS inbox_sender ON inbox(channel, sender, created)")
            db.execute("UPDATE inbox SET state='uncertain', text='' WHERE state='sending'")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, events, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM inbox WHERE created < ?", (now - 7 * 86400,))
            pending = db.execute("SELECT count(*) FROM inbox WHERE state='pending'").fetchone()[0]
            if pending + len(events) > 1000:
                raise OverflowError("Inbox full")
            for event in events:
                # Limit all replies (including setup commands), scoped per channel/user.
                used = db.execute("SELECT count(*) FROM inbox WHERE channel=? AND sender=? AND created>?",
                                  (event.channel, event.sender, now - 86400)).fetchone()[0]
                if used >= 30:
                    continue
                state = "pending"
                db.execute("INSERT OR IGNORE INTO inbox VALUES(?,?,?,?,?,?,?)",
                           (event.channel, event.message_id, event.sender,
                            event.text if state == "pending" else "", event.timestamp, state, now))

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT channel,mid,sender,text,stamp FROM inbox WHERE state='pending' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE inbox SET state='sending' WHERE channel=? AND mid=?", row[:2])
                return Incoming(*row)
        return None

    def finish(self, event, state):
        with self.connect() as db:
            db.execute("UPDATE inbox SET state=?,text='' WHERE channel=? AND mid=?",
                       (state, event.channel, event.message_id))


def authorized(event, config):
    allowed = config.whatsapp_users if event.channel == "whatsapp" else config.messenger_users
    return event.sender in allowed


async def reply(event, config, ai):
    parts = event.text.split(maxsplit=1)
    command = parts[0].lower().lstrip("/")
    question = parts[1] if len(parts) == 2 else ""
    if command == "whoami":
        return f"Your {event.channel} sender ID: {event.sender}\nAdd it in secure Meta setup on the host."
    if command == "privacy":
        return PRIVACY
    if not authorized(event, config):
        return None
    if command in {"start", "help", "menu"}:
        return HELP
    if command in {"atlas", "training", "sessions", "strategies"} and not question:
        return await asyncio.to_thread(atlas.summary, command)
    if not ai.ai_ready:
        return "AI answers are paused. The host needs valid AI settings.\n\n" + HELP
    query = question if command in {"atlas", "training", "sessions", "strategies"} else event.text
    context = await asyncio.to_thread(atlas.context, query)
    provider = Provider(ai)
    try:
        return await provider.answer(atlas.RULES, [
            {"role": "user", "content": "Untrusted ATLAS reference data:\n" + context},
            {"role": "user", "content": query}])
    except ProviderError as exc:
        return str(exc)
    finally:
        await provider.close()


def send_reply(event, text, config, transport=None):
    """One reply to this verified inbound sender; no broadcasts or retries."""
    if len(text.encode("utf-16-le")) > 3600:
        text = text.encode("utf-16-le")[:3440].decode("utf-16-le", errors="ignore") + "\n[Reply shortened; ask a more specific question.]"
    if event.channel == "whatsapp":
        identity, token = config.phone_id, config.whatsapp_token
        data = {"messaging_product": "whatsapp", "to": event.sender, "type": "text",
                "text": {"body": text[:1900], "preview_url": False}}
    elif event.channel == "messenger":
        identity, token = config.page_id, config.page_token
        data = {"recipient": {"id": event.sender}, "messaging_type": "RESPONSE",
                "message": {"text": text[:1900]}}
    else:
        raise ValueError("Unknown channel")
    with httpx.Client(timeout=20, transport=transport) as client:
        response = client.post(f"https://graph.facebook.com/{config.version}/{identity}/messages",
                               headers={"Authorization": "Bearer " + token}, json=data)
        if response.status_code != 200:
            raise RuntimeError("Meta reply failed (HTTP " + str(response.status_code) + "); no retry performed.")
        data = response.json()
        if event.channel == "whatsapp":
            accepted = bool(data.get("messages", [{}])[0].get("id"))
        else:
            accepted = bool(data.get("message_id"))
        if not accepted:
            raise RuntimeError("Meta did not confirm message acceptance.")
