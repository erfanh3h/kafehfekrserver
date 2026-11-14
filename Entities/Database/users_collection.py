from datetime import datetime

import pymongo

from Commons.static_functions import create_random_user_id


def create_user_json(phone, name="", device_id="") -> dict:
    random_id = create_random_user_id()
    return {'_id': random_id, 'phone': phone, 'username': name, "score": 0, "xp": 0, "coin": 50, "image": 0, "token": 0,
            "win_streak": 0, "last_daily_win": datetime(2000, 1, 1),
            "open_game_id": "", "device_id": device_id, "last_time_played": datetime(2000, 1, 1),
            "last_time_chance": datetime(2000, 1, 1), "is_active": True, "join_date": datetime.now()}


class UsersCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def is_phone_avaialble(self, phone_number: str):
        phone_str = str(phone_number).strip().replace(" ", "")
        variants = [phone_str]
        if phone_str.startswith("+98"):
            variants.append("0" + phone_str[3:])
            variants.append(phone_str[3:])
        elif phone_str.startswith("09"):
            variants.append("+98" + phone_str[1:])
            variants.append(phone_str[1:])
        elif phone_str.startswith("9"):
            variants.append("0" + phone_str)
            variants.append("+98" + phone_str)

        query = {'phone': {'$in': variants}}
        return self.collection.find_one(query)

    def create_user(self, phone, name="", device_id="0"):
        data = self.is_phone_avaialble(phone)
        if data is None:
            if str(phone).startswith("bot_") or str(name).startswith("bot_") or str(phone).startswith("test_bot"):
                return None, False
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
        return self.is_phone_avaialble(user_phone)

    def read_users(self, users):
        query = {'_id': {"$in": users}}
        user_Data = self.collection.find(query)
        result = []
        for user in user_Data:
            result.append(user)
        return result

    def read_ranking_users_by_score(self):
        query = {'score': {'$gt': 0}, '_id': {'$ne': '3goBRU', '$not': {'$regex': '^bot_'}}}
        selection_items = {"username": 1, "image": 1, "score": 1, "join_date": 1}
        data = self.collection.find(query, selection_items).sort([('score', pymongo.DESCENDING)]).limit(25)
        return data

    def read_ranking_users_by_win(self, users_id: list):
        clean_ids = [uid for uid in users_id if not (str(uid).startswith("bot_") or str(uid).startswith("test_bot") or str(uid) == "3goBRU")]
        query = {'_id': {'$in': clean_ids}}
        selection_items = {"username": 1, "image": 1, "join_date": 1}
        data = list(self.collection.find(query, selection_items))
        return data

    def read_global_user_data(self, user_id):
        query = {'_id': user_id}
        selection_items = {"username": 1, "xp": 1, "image": 1, "score": 1, "join_date": 1}
        data = self.collection.find_one(query, selection_items)
        return data

    def update_user(self, user_id, username=None, score=None, xp=None, coin=None, image=None, token=None,
                    open_game_id=None, device_id=None, last_time_played=None, last_time_chance=None, is_active=None,
                    win_streak=None, last_daily_win=None):
        if str(user_id).startswith("bot_") or str(user_id).startswith("test_bot"):
            return None
        query = {'_id': user_id}
        update_data = {}
        if username is not None:
            update_data['username'] = username
        if score is not None:
            update_data['score'] = max(0, int(score))
        if xp is not None:
            update_data['xp'] = max(0, int(xp))
        if coin is not None:
            update_data['coin'] = max(0, int(coin))
        if win_streak is not None:
            update_data['win_streak'] = max(0, int(win_streak))
        if last_daily_win is not None:
            update_data['last_daily_win'] = last_daily_win
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

    def reset_users(self):
        self.collection.update_many({}, {'$set': {'xp': 0, 'score': 0}})

    def reset_coins(self):
        query = {'coin': {'$lt': 50}}
        self.collection.update_many(query, {'$set': {'coin': 50}})

    def search_users(self, query_text: str, exclude_ids: list | set | None = None, limit: int = 25) -> list[dict]:
        q_str = str(query_text or "").strip()
        if not q_str:
            return []
        excluded = set(str(x) for x in (exclude_ids or []))
        excluded.add("3goBRU")
        q = {
            "_id": {"$nin": list(excluded), "$not": {"$regex": "^bot_|^test_bot"}},
            "$or": [
                {"_id": {"$regex": q_str, "$options": "i"}},
                {"username": {"$regex": q_str, "$options": "i"}},
            ],
        }
        selection = {
            "_id": 1,
            "username": 1,
            "image": 1,
            "score": 1,
            "xp": 1,
            "join_date": 1,
            "profile_frame": 1,
            "profile_title": 1,
            "profile_badge": 1,
            "status_message": 1,
            "privacy": 1,
        }
        cursor = self.collection.find(q, selection).sort([("score", pymongo.DESCENDING)]).limit(max(1, min(limit, 50)))
        return list(cursor)

    def update_social_customization(
        self,
        user_id: str,
        profile_frame: int | None = None,
        profile_title: str | None = None,
        profile_badge: str | None = None,
        status_message: str | None = None,
        privacy: dict | None = None,
    ) -> dict | None:
        uid = str(user_id)
        if uid.startswith("bot_") or uid.startswith("test_bot"):
            return None
        upd = {}
        if profile_frame is not None:
            upd["profile_frame"] = max(0, int(profile_frame))
        if profile_title is not None:
            upd["profile_title"] = str(profile_title).strip()[:40]
        if profile_badge is not None:
            upd["profile_badge"] = str(profile_badge).strip()[:40]
        if status_message is not None:
            upd["status_message"] = str(status_message).strip()[:120]
        if isinstance(privacy, dict):
            clean_priv = {
                "allow_friend_requests": bool(privacy.get("allow_friend_requests", True)),
                "allow_dms": str(privacy.get("allow_dms", "everyone")),  # everyone | friends | none
                "show_last_seen": bool(privacy.get("show_last_seen", True)),
                "show_current_game": bool(privacy.get("show_current_game", True)),
                "show_match_history": bool(privacy.get("show_match_history", True)),
            }
            upd["privacy"] = clean_priv
        if upd:
            self.collection.find_one_and_update({"_id": uid}, {"$set": upd})
        return self.read_user(uid)
