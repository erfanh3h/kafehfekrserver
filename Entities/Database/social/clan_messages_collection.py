from datetime import datetime
import pymongo
from Commons.static_functions import create_random_name


class ClanMessagesCollectionManager:
    """Persistent Clan Chat storage with pagination, mentions, system events, and moderation."""

    def __init__(self, collection):
        self.collection = collection
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.create_index([("clan_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        except Exception:
            pass

    def create_message(
        self,
        clan_id: str,
        sender_id: str,
        sender_name: str,
        sender_image: int,
        sender_role: str,
        text: str,
        msg_type: str = "text",
        mentions: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict:
        now = datetime.now()
        doc = {
            "_id": f"cmsg_{create_random_name()}",
            "clan_id": str(clan_id),
            "sender_id": str(sender_id),
            "sender_name": str(sender_name),
            "sender_image": int(sender_image or 0),
            "sender_role": str(sender_role or "member"),
            "text": str(text or "").strip()[:500],
            "msg_type": str(msg_type or "text"),  # "text" | "system" | "announcement" | "challenge"
            "mentions": list(mentions or []),
            "metadata": metadata or {},
            "is_deleted": False,
            "deleted_by": "",
            "created_at": now,
        }
        self.collection.insert_one(doc)
        return doc

    def read_message(self, message_id: str):
        return self.collection.find_one({"_id": str(message_id)})

    def get_clan_messages(self, clan_id: str, skip: int = 0, limit: int = 50) -> list[dict]:
        cursor = (
            self.collection.find({"clan_id": str(clan_id), "is_deleted": False})
            .sort("created_at", -1)
            .skip(max(0, int(skip)))
            .limit(max(1, min(int(limit), 100)))
        )
        items = list(cursor)
        items.reverse()
        return items

    def delete_message(self, message_id: str, deleted_by: str) -> bool:
        res = self.collection.find_one_and_update(
            {"_id": str(message_id)},
            {"$set": {"is_deleted": True, "text": "[پیام توسط مدیر کلن حذف شد]", "deleted_by": str(deleted_by)}},
        )
        return res is not None
