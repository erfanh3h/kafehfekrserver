from datetime import datetime, timedelta
import pymongo
from Commons.static_functions import create_random_name


INVITATION_TTL_SECONDS = 180


class InvitationsCollectionManager:
    """Manages multiplayer game & lobby invitations with expiration and duplicate prevention."""

    def __init__(self, collection):
        self.collection = collection
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.create_index(
                [("to_user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING), ("expires_at", pymongo.DESCENDING)]
            )
            self.collection.create_index([("from_user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
        except Exception:
            pass

    def expire_stale_invitations(self):
        now = datetime.now()
        try:
            self.collection.update_many(
                {"status": "pending", "expires_at": {"$lt": now}},
                {"$set": {"status": "expired", "updated_at": now}},
            )
        except Exception:
            pass

    def get_active_duplicate(self, from_user_id: str, to_user_id: str, lobby_id: str = "", game_type: str = ""):
        self.expire_stale_invitations()
        now = datetime.now()
        q = {
            "from_user_id": str(from_user_id),
            "to_user_id": str(to_user_id),
            "status": "pending",
            "expires_at": {"$gt": now},
        }
        if lobby_id:
            q["lobby_id"] = str(lobby_id)
        elif game_type:
            q["game_type"] = str(game_type)
        return self.collection.find_one(q)

    def create_invitation(
        self,
        from_user_id: str,
        from_username: str,
        from_image: int,
        to_user_id: str,
        invite_mode: str = "lobby",
        game_type: str = "Ludo",
        lobby_id: str = "",
        lobby_password: str = "",
        player_count: int = 2,
        clan_id: str = "",
    ) -> dict:
        dup = self.get_active_duplicate(from_user_id, to_user_id, lobby_id, game_type)
        if dup:
            return dup
        now = datetime.now()
        doc = {
            "_id": f"ginv_{create_random_name()}",
            "from_user_id": str(from_user_id),
            "from_username": str(from_username),
            "from_image": int(from_image or 0),
            "to_user_id": str(to_user_id),
            "invite_mode": str(invite_mode or "lobby"),  # "lobby" | "direct_match" | "clan_challenge"
            "game_type": str(game_type or "Ludo"),
            "lobby_id": str(lobby_id or ""),
            "lobby_password": str(lobby_password or ""),
            "player_count": max(2, min(int(player_count or 2), 4)),
            "clan_id": str(clan_id or ""),
            "status": "pending",
            "created_at": now,
            "expires_at": now + timedelta(seconds=INVITATION_TTL_SECONDS),
            "updated_at": now,
        }
        self.collection.insert_one(doc)
        return doc

    def read_invitation(self, invite_id: str):
        self.expire_stale_invitations()
        return self.collection.find_one({"_id": str(invite_id)})

    def update_status(self, invite_id: str, status: str, extra: dict | None = None):
        upd = {"status": str(status), "updated_at": datetime.now()}
        if extra:
            upd.update(extra)
        return self.collection.find_one_and_update({"_id": str(invite_id)}, {"$set": upd})

    def get_incoming_invitations(self, user_id: str) -> list[dict]:
        self.expire_stale_invitations()
        now = datetime.now()
        cursor = self.collection.find(
            {"to_user_id": str(user_id), "status": "pending", "expires_at": {"$gt": now}}
        ).sort("created_at", -1)
        return list(cursor)
