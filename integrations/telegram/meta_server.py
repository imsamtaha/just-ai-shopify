"""Local Meta webhook bridge. Publish only /meta/webhook through an HTTPS proxy."""
import asyncio
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib.parse import parse_qs, urlsplit

from configure import protect_file
from just_ai.config import ROOT, load_settings
from just_ai.meta_config import load_meta
from just_ai.meta_channels import Inbox, incoming, authorized, valid_signature, reply, send_reply
from just_ai.runtime import instance_lock, safe_logging


class Bridge:
    def __init__(self, config, ai, inbox):
        self.config, self.ai, self.inbox = config, ai, inbox
        self.stop = threading.Event()

    def receive(self, body, signature):
        if not self.config.webhook_ready:
            return 503
        if not valid_signature(body, signature, self.config.app_secret):
            return 403
        try:
            events = incoming(json.loads(body), self.config)
            events = [event for event in events if authorized(event, self.config) or
                      event.text.split(maxsplit=1)[0].lstrip('/').lower() in {"whoami", "privacy"}]
            self.inbox.enqueue(events)
            return 200
        except OverflowError:
            return 503
        except (ValueError, KeyError, TypeError, AttributeError, IndexError):
            return 400

    def work(self):
        while not self.stop.is_set():
            event = None
            try:
                event = self.inbox.claim()
                if event is None:
                    self.stop.wait(0.5)
                    continue
                if not -60 <= time.time() - event.timestamp <= 300:
                    self.inbox.finish(event, "expired")
                    continue
                text = asyncio.run(reply(event, self.config, self.ai))
                if text:
                    send_reply(event, text, self.config)
                self.inbox.finish(event, "accepted" if text else "ignored")
            except Exception as exc:
                # Raw URLs, payloads, provider responses and sender IDs are never logged.
                print("Meta worker issue (" + type(exc).__name__ + "); details hidden; no automatic resend.", flush=True)
                if event:
                    try:
                        self.inbox.finish(event, "uncertain")
                    except Exception:
                        pass
                self.stop.wait(1)


def handler_for(bridge):
    class Handler(BaseHTTPRequestHandler):
        server_version = "JUSTAI"

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass

        def respond(self, status, body=""):
            raw = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path == "/health":
                config = bridge.config
                return self.respond(200, json.dumps({"service": "JUST AI Meta bridge",
                    "configured": config.webhook_ready,
                    "whatsapp_configured": config.enabled("whatsapp"),
                    "messenger_configured": config.enabled("messenger"),
                    "ai_configured": bridge.ai.ai_ready,
                    "live_delivery_verified": False}))
            if path.path != "/meta/webhook":
                return self.respond(404)
            query = parse_qs(path.query)
            token = query.get("hub.verify_token", [""])[0]
            if (bridge.config.webhook_ready and query.get("hub.mode") == ["subscribe"] and
                    hmac.compare_digest(token.encode(), bridge.config.verify_token.encode())):
                return self.respond(200, query.get("hub.challenge", [""])[0][:512])
            self.respond(403)

        def do_POST(self):
            if urlsplit(self.path).path != "/meta/webhook":
                return self.respond(404)
            if self.headers.get("Transfer-Encoding"):
                return self.respond(400)
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.respond(415)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 1_000_000:
                    return self.respond(413)
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return self.respond(400)
                status = bridge.receive(raw, self.headers.get("X-Hub-Signature-256", ""))
                self.respond(status, "EVENT_RECEIVED" if status == 200 else "")
            except (ValueError, TimeoutError):
                self.respond(400)
            except Exception:
                self.respond(503)
    return Handler


def main():
    safe_logging()
    config = load_meta()
    ai = load_settings(environ={}, require_telegram=False)
    with instance_lock(ROOT / "data" / "meta.lock"):
        inbox = Inbox(ROOT / "data" / "meta-inbox.sqlite3")
        protect_file(inbox.path)
        bridge = Bridge(config, ai, inbox)
        server = ThreadingHTTPServer(("127.0.0.1", 4382), handler_for(bridge))
        server.daemon_threads = True
        worker = threading.Thread(target=bridge.work, daemon=True)
        worker.start()
        print("Meta bridge: http://127.0.0.1:4382/health", flush=True)
        print("State: " + ("configured; live delivery unverified" if config.webhook_ready else "secure setup required"), flush=True)
        try:
            server.serve_forever()
        finally:
            bridge.stop.set()
            server.server_close()
            worker.join(timeout=85)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print("Meta bridge stopped (" + type(exc).__name__ + "); details hidden.")
