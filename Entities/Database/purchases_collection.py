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

    def create_purchase(self, user_id, product_id, market_type, token):
        user_data = create_purchases_json(user_id, product_id, market_type, token)
        self.collection.insert_one(user_data)
        return user_data

    def read_user_purchases(self, user_id):
        try:
            query = {'_id': user_id}
            user_Data = self.collection.find(query)
            return user_Data
        except:
            return None

    def update_purchase(self, user_id, purchase_id):
        pass

    def delete_purchase(self, purchase_id):
        query = {'_id': purchase_id}
        self.collection.delete_one(query)
