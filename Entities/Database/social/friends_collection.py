from datetime import datetime
import pymongo
from Commons.static_functions import create_random_name


def _pair_key(user_a: str, user_b: str) -> str:
    a, b = str(user_a).strip(), str(user_b).strip()
    return f"{a}:{b}" if a < b else f"{b}:{a}"


class FriendsCollectionManager:
    """Manages friendships, friend_requests, and user_blocks collections."""

    def __init__(self, friendships_col, requests_col, blocks_col):
        self.friendships = friendships_col
        self.requests = requests_col
        self.blocks = blocks_col
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.friendships.create_index([("pair_key", pymongo.ASCENDING)], unique=True)
            self.friendships.create_index([("users", pymongo.ASCENDING)])
            self.requests.create_index(
                [("from_user_id", pymongo.ASCENDING), ("to_user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]
            )
            self.requests.create_index([("to_user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
            self.blocks.create_index(
                [("blocker_id", pymongo.ASCENDING), ("blocked_id", pymongo.ASCENDING)], unique=True
            )
            self.blocks.create_index([("blocked_id", pymongo.ASCENDING)])
        except Exception:
            pass

    # --- Blocking ---
    def is_blocked(self, user_a: str, user_b: str) -> bool:
        a, b = str(user_a), str(user_b)
        doc = self.blocks.find_one(
            {"$or": [{"blocker_id": a, "blocked_id": b}, {"blocker_id": b, "blocked_id": a}]}
        )
        return doc is not None

    def has_user_blocked(self, blocker_id: str, blocked_id: str) -> bool:
        return self.blocks.find_one({"blocker_id": str(blocker_id), "blocked_id": str(blocked_id)}) is not None

    def get_blocked_ids(self, blocker_id: str) -> list[str]:
        cursor = self.blocks.find({"blocker_id": str(blocker_id)})
        return [str(doc.get("blocked_id", "")) for doc in cursor if doc.get("blocked_id")]

    def get_all_block_related_ids(self, user_id: str) -> set[str]:
        uid = str(user_id)
        cursor = self.blocks.find({"$or": [{"blocker_id": uid}, {"blocked_id": uid}]})
        out: set[str] = set()
        for doc in cursor:
            if str(doc.get("blocker_id")) == uid:
                out.add(str(doc.get("blocked_id")))
            else:
                out.add(str(doc.get("blocker_id")))
        return out

    def block_user(self, blocker_id: str, blocked_id: str, reason: str = "") -> dict:
        b1, b2 = str(blocker_id), str(blocked_id)
        if b1 == b2:
            return {"ok": False, "error": "cannot_block_self"}
        now = datetime.now()
        # Remove any existing friendship or pending friend requests between them
        self.remove_friendship(b1, b2)
        self.requests.update_many(
            {
                "$or": [
                    {"from_user_id": b1, "to_user_id": b2, "status": "pending"},
                    {"from_user_id": b2, "to_user_id": b1, "status": "pending"},
                ]
            },
            {"$set": {"status": "canceled", "updated_at": now}},
        )
        doc = {
            "_id": f"blk_{b1}_{b2}",
            "blocker_id": b1,
            "blocked_id": b2,
            "reason": str(reason or "")[:200],
            "created_at": now,
        }
        try:
            self.blocks.find_one_and_update(
                {"blocker_id": b1, "blocked_id": b2},
                {"$set": doc},
                upsert=True,
            )
        except Exception:
            pass
        return {"ok": True, "blocked_id": b2}

    def unblock_user(self, blocker_id: str, blocked_id: str) -> bool:
        res = self.blocks.delete_one({"blocker_id": str(blocker_id), "blocked_id": str(blocked_id)})
        return getattr(res, "deleted_count", 0) > 0

    # --- Friendships ---
    def are_friends(self, user_a: str, user_b: str) -> bool:
        pk = _pair_key(user_a, user_b)
        return self.friendships.find_one({"pair_key": pk}) is not None

    def get_friend_ids(self, user_id: str) -> list[str]:
        uid = str(user_id)
        cursor = self.friendships.find({"users": uid}).sort("created_at", -1)
        out: list[str] = []
        for doc in cursor:
            for u in doc.get("users", []):
                if str(u) != uid:
                    out.append(str(u))
        return out

    def create_friendship(self, user_a: str, user_b: str) -> dict:
        a, b = str(user_a), str(user_b)
        pk = _pair_key(a, b)
        existing = self.friendships.find_one({"pair_key": pk})
        if existing:
            return existing
        now = datetime.now()
        doc = {
            "_id": f"fr_{create_random_name()}",
            "pair_key": pk,
            "users": sorted([a, b]),
            "created_at": now,
        }
        try:
            self.friendships.insert_one(doc)
        except Exception:
            existing = self.friendships.find_one({"pair_key": pk})
            if existing:
                return existing
        return doc

    def remove_friendship(self, user_a: str, user_b: str) -> bool:
        pk = _pair_key(user_a, user_b)
        res = self.friendships.delete_one({"pair_key": pk})
        return getattr(res, "deleted_count", 0) > 0

    # --- Friend Requests ---
    def get_pending_request_between(self, user_a: str, user_b: str):
        a, b = str(user_a), str(user_b)
        return self.requests.find_one(
            {
                "status": "pending",
                "$or": [
                    {"from_user_id": a, "to_user_id": b},
                    {"from_user_id": b, "to_user_id": a},
                ],
            }
        )

    def create_friend_request(self, from_user_id: str, to_user_id: str, message: str = "") -> dict:
        f_id, t_id = str(from_user_id), str(to_user_id)
        now = datetime.now()
        doc = {
            "_id": f"freq_{create_random_name()}",
            "from_user_id": f_id,
            "to_user_id": t_id,
            "message": str(message or "").strip()[:160],
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        self.requests.insert_one(doc)
        return doc

    def read_request(self, request_id: str):
        return self.requests.find_one({"_id": str(request_id)})

    def update_request_status(self, request_id: str, new_status: str):
        now = datetime.now()
        self.requests.find_one_and_update(
            {"_id": str(request_id)},
            {"$set": {"status": new_status, "updated_at": now}},
        )

    def get_incoming_requests(self, user_id: str, limit: int = 50) -> list[dict]:
        cursor = (
            self.requests.find({"to_user_id": str(user_id), "status": "pending"})
            .sort("created_at", -1)
            .limit(max(1, min(limit, 100)))
        )
        return list(cursor)

    def get_outgoing_requests(self, user_id: str, limit: int = 50) -> list[dict]:
        cursor = (
            self.requests.find({"from_user_id": str(user_id), "status": "pending"})
            .sort("created_at", -1)
            .limit(max(1, min(limit, 100)))
        )
        return list(cursor)
