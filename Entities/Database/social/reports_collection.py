from datetime import datetime
import pymongo
from Commons.static_functions import create_random_name


class ReportsCollectionManager:
    """Manages player and chat message reports for moderation."""

    def __init__(self, collection):
        self.collection = collection
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.create_index([("target_user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
            self.collection.create_index([("reporter_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        except Exception:
            pass

    def create_report(
        self,
        reporter_id: str,
        target_user_id: str,
        reason: str,
        target_type: str = "player",
        target_id: str = "",
        details: str = "",
    ) -> dict:
        now = datetime.now()
        doc = {
            "_id": f"rep_{create_random_name()}",
            "reporter_id": str(reporter_id),
            "target_user_id": str(target_user_id),
            "target_type": str(target_type or "player"),  # "player" | "dm" | "clan_message" | "clan"
            "target_id": str(target_id or ""),
            "reason": str(reason or "spam")[:80],
            "details": str(details or "")[:400],
            "status": "open",
            "created_at": now,
        }
        self.collection.insert_one(doc)
        return doc
