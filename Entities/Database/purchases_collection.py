from datetime import datetime

import pymongo

from Commons.static_functions import create_random_user_id
from Entities.Games.game_types import GameTypesEnum


def create_purchases_json(user_id, product_id, market_type, token) -> dict:
    random_id = create_random_user_id(length=8)
    result = {'_id': random_id, "user_id": user_id, "product_id": product_id, "market_type": market_type,
              "token": token, "date": datetime.now()}
    return result


class PurchasesCollectionManager:
    def __init__(self, collection):
        self.collection = collection
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.create_index([("market_type", pymongo.ASCENDING), ("token", pymongo.ASCENDING)])
            self.collection.create_index([("user_id", pymongo.ASCENDING), ("date", pymongo.DESCENDING)])
        except Exception:
            pass

    def has_purchase_token(self, market_type: str, token: str) -> bool:
        tok = str(token or "").strip()
        if not tok:
            return False
        try:
            return self.collection.find_one({"market_type": str(market_type), "token": tok}, {"_id": 1}) is not None
        except Exception:
            return False

    def create_purchase(self, user_id, product_id, market_type, token):
        user_data = create_purchases_json(user_id, product_id, market_type, token)
        self.collection.insert_one(user_data)
        return user_data

    def read_user_purchases(self, user_id):
        try:
            query = {'user_id': user_id}
            user_Data = self.collection.find(query)
            return list(user_Data)
        except Exception:
            return []

    def update_purchase(self, user_id, purchase_id):
        pass

    def delete_purchase(self, purchase_id):
        query = {'_id': purchase_id}
        self.collection.delete_one(query)
