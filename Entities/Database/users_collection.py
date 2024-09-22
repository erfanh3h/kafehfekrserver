from datetime import datetime

import pymongo

from Commons.static_functions import create_random_user_id


def create_user_json(phone, name="", device_id="") -> dict:
    random_id = create_random_user_id()
    return {'_id': random_id, 'phone': phone, 'username': name, "score": 0, "xp": 0, "coin": 50, "image": 0, "token": 0,
            "open_game_id": "", "device_id": device_id, "last_time_played": datetime(2000, 1, 1),
            "last_time_chance": datetime(2000, 1, 1), "is_active": True, "join_date": datetime.now()}


class UsersCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def is_phone_avaialble(self, phone_number: str):
        if len(phone_number) != 10:
            return False
        if phone_number[0] != "9":
            return False
        query = {'phone': phone_number}
        return self.collection.find_one(query)

    def create_user(self, phone, name="", device_id="0"):
        data = self.is_phone_avaialble(phone)
        if data is None:
            user_data = create_user_json(phone=phone, name=name, device_id=device_id)
            self.collection.insert_one(user_data)
            return user_data, True
        else:
            return data, False

    def read_user(self, user_id):
        query = {'_id': user_id}
        user_Data = self.collection.find_one(query)
        return user_Data

    def read_user_by_phone(self, user_phone):
        query = {'phone': user_phone}
        user_Data = self.collection.find_one(query)
        return user_Data

    def read_users(self, users):
        query = {'_id': {"$in": users}}
        user_Data = self.collection.find(query)
        result = []
        for user in user_Data:
            result.append(user)
        return result

    def read_ranking_users_by_score(self):
        query = {'score': {'$gt': 0}}
        selection_items = {"username": 1, "image": 1, "score": 1, "join_date": 1}
        data = self.collection.find(query, selection_items).sort([('score', pymongo.DESCENDING)]).limit(25)
        return data

    def read_ranking_users_by_win(self, users_id: list):
        query = {'_id': {'$in': users_id}}
        selection_items = {"username": 1, "image": 1, "join_date": 1}
        data = list(self.collection.find(query, selection_items))
        return data

    def read_global_user_data(self, user_id):
        query = {'_id': user_id}
        selection_items = {"username": 1, "xp": 1, "image": 1, "score": 1, "join_date": 1}
        data = self.collection.find_one(query, selection_items)
        return data

    def update_user(self, user_id, username=None, score=None, xp=None, coin=None, image=None, token=None,
                    open_game_id=None, device_id=None, last_time_played=None, last_time_chance=None, is_active=None):
        query = {'_id': user_id}
        update_data = {}
        if username is not None:
            update_data['username'] = username
        if score is not None and score >= 0:
            update_data['score'] = int(score)
        if xp is not None and xp >= 0:
            update_data['xp'] = int(xp)
        if coin is not None and coin >= 0:
            update_data['coin'] = int(coin)
        if image is not None:
            update_data['image'] = int(image)
        if token is not None:
            update_data['token'] = token
        if open_game_id is not None:
            update_data['open_game_id'] = open_game_id
        if device_id is not None:
            update_data['device_id'] = device_id
        if last_time_played is not None:
            update_data['last_time_played'] = last_time_played
        if last_time_chance is not None:
            update_data['last_time_chance'] = last_time_chance
        if is_active is not None:
            update_data['is_active'] = is_active
        self.collection.find_one_and_update(query, {'$set': update_data})

    def delete_user(self, user_id):
        query = {'_id': user_id}
        self.collection.delete_one(query)

    def reset_all_users_active_games(self):
        query = {}
        update_data = {'open_game_id': ""}
        self.collection.find_one_and_update(query, {'$set': update_data})

    def get_count_of_users(self):
        return self.collection.count_documents({})
