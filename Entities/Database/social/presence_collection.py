from datetime import datetime, timedelta
import pymongo


VALID_PRESENCE_STATUSES = ("online", "in_game", "in_lobby", "in_queue", "away", "offline")


class PresenceCollectionManager:
    """Session-based player presence tracking across multiple Socket.IO namespaces."""

    def __init__(self, collection):
        self.collection = collection
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.create_index([("status", pymongo.ASCENDING), ("last_seen", pymongo.DESCENDING)])
        except Exception:
            pass

    def update_presence(
        self,
        user_id: str,
        status: str,
        current_game_type: str = "",
        current_game_id: str = "",
        current_lobby_id: str = "",
        socket_id: str = "",
        add_socket: bool = True,
    ) -> dict:
        uid = str(user_id)
        st = status if status in VALID_PRESENCE_STATUSES else "online"
        now = datetime.now()
        existing = self.collection.find_one({"_id": uid}) or {}
        active_sockets = list(existing.get("active_sockets", []) or [])
        if socket_id:
            if add_socket:
                if socket_id not in active_sockets:
                    active_sockets.append(socket_id)
            else:
                active_sockets = [s for s in active_sockets if s != socket_id]
                if active_sockets and st == "offline":
                    # Still has another active socket connection!
                    st = existing.get("status", "online")
                    if st == "offline":
                        st = "online"

        doc = {
            "_id": uid,
            "user_id": uid,
            "status": st,
            "current_game_type": str(current_game_type if st == "in_game" else ""),
            "current_game_id": str(current_game_id if st == "in_game" else ""),
            "current_lobby_id": str(current_lobby_id if st == "in_lobby" else ""),
            "active_sockets": active_sockets[-10:],
            "last_seen": now,
            "updated_at": now,
        }
        self.collection.find_one_and_update({"_id": uid}, {"$set": doc}, upsert=True)
        return doc

    def get_presence(self, user_id: str) -> dict:
        uid = str(user_id)
        doc = self.collection.find_one({"_id": uid})
        if not doc:
            return {
                "user_id": uid,
                "status": "offline",
                "current_game_type": "",
                "current_game_id": "",
                "current_lobby_id": "",
                "last_seen": None,
            }
        # Auto-expire stale online presence if no update in 15 minutes
        last_seen = doc.get("last_seen")
        st = str(doc.get("status", "offline"))
        if st != "offline" and isinstance(last_seen, datetime):
            if datetime.now() - last_seen > timedelta(minutes=15):
                st = "offline"
        return {
            "user_id": uid,
            "status": st,
            "current_game_type": str(doc.get("current_game_type", "")) if st == "in_game" else "",
            "current_game_id": str(doc.get("current_game_id", "")) if st == "in_game" else "",
            "current_lobby_id": str(doc.get("current_lobby_id", "")) if st == "in_lobby" else "",
            "last_seen": last_seen.isoformat() if hasattr(last_seen, "isoformat") else str(last_seen or ""),
        }

    def get_bulk_presence(self, user_ids: list[str]) -> dict[str, dict]:
        clean = [str(u) for u in user_ids if u]
        if not clean:
            return {}
        out: dict[str, dict] = {}
        now = datetime.now()
        for doc in self.collection.find({"_id": {"$in": clean}}):
            uid = str(doc["_id"])
            last_seen = doc.get("last_seen")
            st = str(doc.get("status", "offline"))
            if st != "offline" and isinstance(last_seen, datetime):
                if now - last_seen > timedelta(minutes=15):
                    st = "offline"
            out[uid] = {
                "user_id": uid,
                "status": st,
                "current_game_type": str(doc.get("current_game_type", "")) if st == "in_game" else "",
                "current_game_id": str(doc.get("current_game_id", "")) if st == "in_game" else "",
                "current_lobby_id": str(doc.get("current_lobby_id", "")) if st == "in_lobby" else "",
                "last_seen": last_seen.isoformat() if hasattr(last_seen, "isoformat") else str(last_seen or ""),
            }
        for uid in clean:
            if uid not in out:
                out[uid] = {
                    "user_id": uid,
                    "status": "offline",
                    "current_game_type": "",
                    "current_game_id": "",
                    "current_lobby_id": "",
                    "last_seen": "",
                }
        return out

    def update_activity(self, user_id: str, status: str = "online", current_game_type: str = "", current_game_id: str = "", current_lobby_id: str = "") -> dict:
        return self.update_presence(
            user_id=user_id,
            status=status,
            current_game_type=current_game_type,
            current_game_id=current_game_id,
            current_lobby_id=current_lobby_id,
        )
