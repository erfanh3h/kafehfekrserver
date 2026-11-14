from Entities.Database import game_database
from Entities.Api_Services.social.security import serialize_dt


def _format_notification(n: dict) -> dict:
    return {
        "notification_id": str(n["_id"]),
        "type": str(n.get("type", "")),
        "category": str(n.get("category", "")),
        "title": str(n.get("title", "")),
        "body": str(n.get("body", "")),
        "actor_id": str(n.get("actor_id", "")),
        "actor_name": str(n.get("actor_name", "")),
        "actor_image": int(n.get("actor_image", 0) or 0),
        "payload": n.get("payload", {}) or {},
        "is_read": bool(n.get("is_read", False)),
        "created_at": serialize_dt(n.get("created_at")),
    }


def list_notifications(user_id: str, skip: int = 0, limit: int = 40, unread_only: bool = False) -> dict:
    uid = str(user_id)
    docs = game_database.notifications_manager.get_notifications(uid, skip=skip, limit=limit, unread_only=unread_only)
    unread_cnt = game_database.notifications_manager.get_unread_count(uid)
    dm_unread = game_database.direct_messages_manager.get_total_unread_count(uid)
    return {
        "notifications": [_format_notification(d) for d in docs],
        "unread_count": unread_cnt,
        "unread_dm_count": dm_unread,
        "preferences": game_database.notifications_manager.get_preferences(uid),
    }


def mark_notification_read(user_id: str, notification_id: str) -> dict:
    ok = game_database.notifications_manager.mark_read(user_id, notification_id)
    return {
        "marked": ok,
        "unread_count": game_database.notifications_manager.get_unread_count(user_id),
    }


def mark_all_notifications_read(user_id: str) -> dict:
    cnt = game_database.notifications_manager.mark_all_read(user_id)
    return {"marked_count": cnt, "unread_count": 0}


def update_notification_preferences(user_id: str, prefs: dict) -> dict:
    updated = game_database.notifications_manager.update_preferences(user_id, prefs)
    return {"preferences": updated}
