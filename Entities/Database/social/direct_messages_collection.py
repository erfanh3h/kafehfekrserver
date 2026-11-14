from datetime import datetime
import pymongo
from Commons.static_functions import create_random_name


def _conv_id(user_a: str, user_b: str) -> str:
    a, b = str(user_a).strip(), str(user_b).strip()
    return f"dm_{a}_{b}" if a < b else f"dm_{b}_{a}"


class DirectMessagesCollectionManager:
    """Manages 1-to-1 private conversations and direct messages with unread counts and read receipts."""

    def __init__(self, conversations_col, messages_col):
        self.conversations = conversations_col
        self.messages = messages_col
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.conversations.create_index([("participants", pymongo.ASCENDING), ("updated_at", pymongo.DESCENDING)])
            self.messages.create_index([("conversation_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
            self.messages.create_index([("to_user_id", pymongo.ASCENDING), ("is_read", pymongo.ASCENDING)])
        except Exception:
            pass

    def get_conversation_id(self, user_a: str, user_b: str) -> str:
        return _conv_id(user_a, user_b)

    def get_or_create_conversation(self, user_a: str, user_b: str) -> dict:
        cid = _conv_id(user_a, user_b)
        existing = self.conversations.find_one({"_id": cid})
        if existing:
            return existing
        now = datetime.now()
        doc = {
            "_id": cid,
            "participants": sorted([str(user_a), str(user_b)]),
            "last_message": "",
            "last_sender_id": "",
            "unread_counts": {str(user_a): 0, str(user_b): 0},
            "last_read_at": {},
            "created_at": now,
            "updated_at": now,
        }
        try:
            self.conversations.insert_one(doc)
        except Exception:
            existing = self.conversations.find_one({"_id": cid})
            if existing:
                return existing
        return doc

    def create_direct_message(self, from_user_id: str, to_user_id: str, text: str) -> dict:
        f_id, t_id = str(from_user_id), str(to_user_id)
        conv = self.get_or_create_conversation(f_id, t_id)
        cid = conv["_id"]
        now = datetime.now()
        clean_text = str(text or "").strip()[:500]
        msg_doc = {
            "_id": f"dmsg_{create_random_name()}",
            "conversation_id": cid,
            "from_user_id": f_id,
            "to_user_id": t_id,
            "text": clean_text,
            "is_read": False,
            "read_at": None,
            "is_deleted": False,
            "created_at": now,
        }
        self.messages.insert_one(msg_doc)

        unread_map = dict(conv.get("unread_counts", {}) or {})
        unread_map[t_id] = int(unread_map.get(t_id, 0)) + 1
        unread_map[f_id] = int(unread_map.get(f_id, 0))
        self.conversations.find_one_and_update(
            {"_id": cid},
            {
                "$set": {
                    "last_message": clean_text[:120],
                    "last_sender_id": f_id,
                    "unread_counts": unread_map,
                    "updated_at": now,
                }
            },
        )
        return msg_doc

    def get_user_conversations(self, user_id: str, skip: int = 0, limit: int = 40) -> list[dict]:
        uid = str(user_id)
        cursor = (
            self.conversations.find({"participants": uid})
            .sort("updated_at", -1)
            .skip(max(0, int(skip)))
            .limit(max(1, min(int(limit), 60)))
        )
        return list(cursor)

    def get_conversation_messages(self, user_a: str, user_b: str, skip: int = 0, limit: int = 50) -> list[dict]:
        cid = _conv_id(user_a, user_b)
        cursor = (
            self.messages.find({"conversation_id": cid, "is_deleted": False})
            .sort("created_at", -1)
            .skip(max(0, int(skip)))
            .limit(max(1, min(int(limit), 100)))
        )
        items = list(cursor)
        items.reverse()
        return items

    def mark_conversation_read(self, reader_id: str, partner_id: str) -> int:
        r_id, p_id = str(reader_id), str(partner_id)
        cid = _conv_id(r_id, p_id)
        now = datetime.now()
        self.messages.update_many(
            {"conversation_id": cid, "to_user_id": r_id, "is_read": False},
            {"$set": {"is_read": True, "read_at": now}},
        )
        conv = self.conversations.find_one({"_id": cid})
        if not conv:
            return 0
        unread_map = dict(conv.get("unread_counts", {}) or {})
        cleared = int(unread_map.get(r_id, 0))
        unread_map[r_id] = 0
        read_map = dict(conv.get("last_read_at", {}) or {})
        read_map[r_id] = now.isoformat()
        self.conversations.find_one_and_update(
            {"_id": cid},
            {"$set": {"unread_counts": unread_map, "last_read_at": read_map}},
        )
        return cleared

    def get_total_unread_count(self, user_id: str) -> int:
        uid = str(user_id)
        total = 0
        for conv in self.conversations.find({"participants": uid}):
            u_map = conv.get("unread_counts", {}) or {}
            total += int(u_map.get(uid, 0))
        return total
