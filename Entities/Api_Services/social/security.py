import math
import re
import time
from datetime import datetime
from Entities import Network_Exeptions


# Sliding-window in-memory rate limiter per (user_id, action_key)
_RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}

RATE_LIMIT_RULES: dict[str, tuple[int, float]] = {
    "friend_request": (15, 60.0),      # max 15 requests per 60s
    "dm_send": (30, 60.0),             # max 30 DMs per 60s
    "clan_chat": (30, 60.0),           # max 30 clan messages per 60s
    "game_invite": (15, 60.0),         # max 15 game invites per 60s
    "clan_create": (3, 300.0),         # max 3 clan creations per 5 min
    "report": (10, 300.0),             # max 10 reports per 5 min
}

FORBIDDEN_WORDS = ("admin_system", "system_root", "<script", "javascript:")


def check_rate_limit(user_id: str, action: str) -> None:
    rule = RATE_LIMIT_RULES.get(action)
    if not rule:
        return
    max_calls, window_sec = rule
    now = time.time()
    key = (str(user_id), str(action))
    bucket = [t for t in _RATE_BUCKETS.get(key, []) if now - t < window_sec]
    if len(bucket) >= max_calls:
        raise Network_Exeptions.raise422(details="تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کنید.")
    bucket.append(now)
    _RATE_BUCKETS[key] = bucket


def reset_rate_limits() -> None:
    _RATE_BUCKETS.clear()


def sanitize_text(text: str, max_len: int = 400) -> str:
    s = str(text or "").strip()
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    return s[:max_len]


def validate_safe_name(name: str, min_len: int = 3, max_len: int = 28, field_label: str = "نام") -> str:
    clean = sanitize_text(name, max_len)
    if len(clean) < min_len:
        raise Network_Exeptions.raise422(details=f"{field_label} باید حداقل {min_len} حرف باشد.")
    lower = clean.lower()
    for bad in FORBIDDEN_WORDS:
        if bad in lower:
            raise Network_Exeptions.raise422(details=f"{field_label} انتخاب‌شده مجاز نیست.")
    return clean


def validate_clan_tag(tag: str) -> str:
    raw = str(tag or "").strip().upper()
    if raw.startswith("#"):
        raw = raw[1:].strip()
    raw = re.sub(r"[^A-Z0-9]", "", raw)
    if len(raw) < 3 or len(raw) > 8:
        raise Network_Exeptions.raise422(details="تگ کلن باید بین ۳ تا ۸ حرف انگلیسی یا عدد باشد.")
    return "#" + raw


def calculate_player_level(xp: int) -> int:
    if xp <= 0:
        return 1
    return int(math.floor(math.sqrt(float(xp) / 20.0 + 1.0)))


def calculate_competitive_tier(score: int) -> dict:
    sc = max(0, int(score or 0))
    if sc >= 1500:
        return {"id": "grandmaster", "title": "استاد بزرگ", "min_score": 1500}
    if sc >= 1000:
        return {"id": "diamond", "title": "الماس", "min_score": 1000}
    if sc >= 600:
        return {"id": "gold", "title": "طلایی", "min_score": 600}
    if sc >= 300:
        return {"id": "silver", "title": "نقره‌ای", "min_score": 300}
    if sc >= 100:
        return {"id": "bronze", "title": "برنزی", "min_score": 100}
    return {"id": "novice", "title": "تازه‌کار", "min_score": 0}


def serialize_dt(val) -> str:
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val or "")


def sanitize_public_user_summary(user_doc: dict | None, presence_doc: dict | None = None, clan_doc: dict | None = None) -> dict:
    if not user_doc:
        return {}
    uid = str(user_doc.get("_id", user_doc.get("id", "")))
    xp = int(user_doc.get("xp", 0) or 0)
    score = int(user_doc.get("score", 0) or 0)
    lvl = calculate_player_level(xp)
    tier = calculate_competitive_tier(score)
    priv = user_doc.get("privacy") if isinstance(user_doc.get("privacy"), dict) else {}
    show_last_seen = bool(priv.get("show_last_seen", True))
    show_game = bool(priv.get("show_current_game", True))

    pres = presence_doc or {}
    st = str(pres.get("status", "offline"))
    out = {
        "user_id": uid,
        "_id": uid,
        "username": str(user_doc.get("username", "بازیکن") or "بازیکن"),
        "image": int(user_doc.get("image", 0) or 0),
        "score": score,
        "xp": xp,
        "level": lvl,
        "rank_tier": tier["id"],
        "rank_title": tier["title"],
        "profile_frame": int(user_doc.get("profile_frame", 0) or 0),
        "profile_title": str(user_doc.get("profile_title", "") or ""),
        "profile_badge": str(user_doc.get("profile_badge", "") or ""),
        "status_message": str(user_doc.get("status_message", "") or ""),
        "status": st,
        "current_game_type": str(pres.get("current_game_type", "")) if show_game else "",
        "current_game_id": str(pres.get("current_game_id", "")) if show_game else "",
        "current_lobby_id": str(pres.get("current_lobby_id", "")) if show_game else "",
        "last_seen": str(pres.get("last_seen", "")) if show_last_seen else "",
    }
    if clan_doc:
        out["clan"] = {
            "clan_id": str(clan_doc.get("_id", clan_doc.get("clan_id", ""))),
            "name": str(clan_doc.get("name", "")),
            "tag": str(clan_doc.get("tag", "")),
            "emblem_id": int(clan_doc.get("emblem_id", 1) or 1),
            "role": str(clan_doc.get("role", "member")),
        }
    else:
        out["clan"] = None
    return out
