from Entities.Games.game_types import GameTypesEnum
from datetime import datetime


class ConfigCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def create_config(self):
        data = {'_id': 1, "latest_version": "0.0.1", "allowed_version": "0.0.1"
            , "is_queue_open": True, "release_data": datetime.now()}
        self.collection.insert_one(data)
        return data

    def read_config(self):
        data = self.collection.find_one({})
        return data

    def update_config(self, latest_version=None, allowed_version=None, is_queue_open=None, release_data=None):
        update_data = {}
        if latest_version is not None:
            update_data['latest_version'] = latest_version
        if allowed_version is not None:
            update_data['allowed_version'] = allowed_version
        if is_queue_open is not None:
            update_data['is_queue_open'] = is_queue_open
        if release_data is not None:
            update_data['release_data'] = release_data
        self.collection.find_one_and_update({}, {'$set': update_data})
