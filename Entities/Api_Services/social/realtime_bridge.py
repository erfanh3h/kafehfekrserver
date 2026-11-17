import json
import os
import threading
import urllib.request

from Entities.Security import SECRET_KEY

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:5000").rstrip("/")


def emit_social_realtime(
    events: list[dict] | None = None,
    room_updates_before: list[dict] | None = None,
    room_updates: list[dict] | None = None,
) -> None:
    """Non-blocking bridge from REST server (:5001) to Socket.IO realtime backend (:5000)."""
    payload = {
        "events": events or [],
        "room_updates_before": room_updates_before or [],
        "room_updates": room_updates or [],
    }
    if not payload["events"] and not payload["room_updates_before"] and not payload["room_updates"]:
        return

    def _post():
        try:
            url = f"{BACKEND_INTERNAL_URL}/internal/social/emit"
            body = json.dumps(payload, default=str).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Secret": SECRET_KEY,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                resp.read()
        except Exception:
            pass

    threading.Thread(target=_post, daemon=True).start()
