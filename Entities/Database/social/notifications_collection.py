from datetime import datetime
import pymongo
from Commons.static_functions import create_random_name


DEFAULT_NOTIFICATION_PREFS = {
    "friend_requests": True,
    "friend_online": False,
    "game_invitations": True,
    "clan_invitations": True,
    "clan_events": True,
    "direct_messages": True,
    "achievements": True,
}


class NotificationsCollectionManager:
    """Manages persistent social notifications and per-user notification preferences."""

    def __init__(self, notifications_col, prefs_col):
        self.notifications = notifications_col
        self.prefs = prefs_col
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.notifications.create_index(
                [("user_id", pymongo.ASCENDING), ("is_read", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)]
            )
            self.prefs.create_index([("user_id", pymongo.ASCENDING)], unique=True)
        except Exception:
            pass

    def get_preferences(self, user_id: str) -> dict:
        doc = self.prefs.find_one({"user_id": str(user_id)})
        merged = dict(DEFAULT_NOTIFICATION_PREFS)
        if doc and isinstance(doc.get("prefs"), dict):
            for k in DEFAULT_NOTIFICATION_PREFS:
                if k in doc["prefs"]:
                    merged[k] = bool(doc["prefs"][k])
        return merged

    def update_preferences(self, user_id: str, updates: dict) -> dict:
        cur = self.get_preferences(user_id)
        for k in DEFAULT_NOTIFICATION_PREFS:
            if k in updates and updates[k] is not None:
                cur[k] = bool(updates[k])
        self.prefs.find_one_and_update(
            {"user_id": str(user_id)},
            {"$set": {"user_id": str(user_id), "prefs": cur, "updated_at": datetime.now()}},
            upsert=True,
        )
        return cur

    def should_notify(self, user_id: str, category: str) -> bool:
        prefs = self.get_preferences(user_id)
        return bool(prefs.get(category, True))

    def create_notification(
        self,
        user_id: str,
        notif_type: str,
        title: str,
        body: str,
        actor_id: str = "",
        actor_name: str = "",
        actor_image: int = 0,
        payload: dict | None = None,
        category: str = "",
    ) -> dict | None:
        uid = str(user_id)
        if uid.startswith("bot_") or uid.startswith("test_bot"):
            return None
        cat = category or self._infer_category(notif_type)
        if not self.should_notify(uid, cat):
            return None
        now = datetime.now()
        doc = {
            "_id": f"ntf_{create_random_name()}",
            "user_id": uid,
            "type": str(notif_type),
            "category": cat,
            "title": str(title or "")[:120],
            "body": str(body or "")[:280],
            "actor_id": str(actor_id or ""),
            "actor_name": str(actor_name or ""),
            "actor_image": int(actor_image or 0),
            "payload": payload or {},
            "is_read": False,
            "created_at": now,
        }
        self.notifications.insert_one(doc)
        return doc

    def _infer_category(self, notif_type: str) -> str:
        t = str(notif_type).lower()
        if "friend_online" in t:
            return "friend_online"
        if "friend" in t:
            return "friend_requests"
        if "game_invite" in t or "lobby_invite" in t:
            return "game_invitations"
        if "clan_invite" in t:
            return "clan_invitations"
        if "clan" in t:
            return "clan_events"
        if "dm" in t or "message" in t:
            return "direct_messages"
        if "achievement" in t:
            return "achievements"
        return "clan_events"

    def get_notifications(self, user_id: str, skip: int = 0, limit: int = 40, unread_only: bool = False) -> list[dict]:
        q: dict = {"user_id": str(user_id)}
        if unread_only:
            q["is_read"] = False
        cursor = (
            self.notifications.find(q)
            .sort("created_at", -1)
            .skip(max(0, int(skip)))
            .limit(max(1, min(int(limit), 80)))
        )
        return list(cursor)

    def get_unread_count(self, user_id: str) -> int:
        return self.notifications.count_documents({"user_id": str(user_id), "is_read": False})

    def mark_read(self, user_id: str, notification_id: str) -> bool:
        res = self.notifications.find_one_and_update(
            {"_id": str(notification_id), "user_id": str(user_id)},
            {"$set": {"is_read": True}},
        )
        return res is not None

    def mark_all_read(self, user_id: str) -> int:
        res = self.notifications.update_many(
            {"user_id": str(user_id), "is_read": False},
            {"$set": {"is_read": True}},
        )
        return getattr(res, "modified_count", 0)
