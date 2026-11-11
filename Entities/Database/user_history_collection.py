import pymongo

from Entities.Games.game_types import GameTypesEnum


MODE_HISTORY_KEYS = [
    "win_rank", "draw_rank", "lose_rank",
    "win_classic_rank", "draw_classic_rank", "lose_classic_rank",
    "win_multi_rank", "draw_multi_rank", "lose_multi_rank",
    "rank1_multi_rank", "rank2_multi_rank", "rankn_multi_rank",
]


def create_user_history_json(user_id) -> dict:
    result = {'_id': user_id}
    for k in MODE_HISTORY_KEYS:
        result[k] = 0
    return result


class UserHistoryCollectionManager:
    def __init__(self, collection):
        self.collection = collection
        self.mode_keys: list[str] = list(MODE_HISTORY_KEYS)
        self.game_types: list[str] = []
        for game_type in [game.value for game in GameTypesEnum]:
            self.game_types.append(f'{game_type.lower()}_win')
            self.game_types.append(f'{game_type.lower()}_draw')
            self.game_types.append(f'{game_type.lower()}_lose')
        for legacy in ["ten_win", "ten_draw", "ten_lose"]:
            if legacy not in self.game_types:
                self.game_types.append(legacy)
        for game_type in [game.value for game in GameTypesEnum.multi_players_games()]:
            self.game_types.append(f'{game_type.lower()}_rank1')
            self.game_types.append(f'{game_type.lower()}_rank2')
            self.game_types.append(f'{game_type.lower()}_rankn')

    def create_user_history(self, user_id):
        if str(user_id).startswith("bot_") or str(user_id).startswith("test_bot"):
            return None
        user_data = create_user_history_json(user_id)
        try:
            self.collection.insert_one(user_data)
        except Exception:
            pass
        return user_data

    def read_user_history(self, user_id):
        try:
            query = {'_id': user_id}
            user_Data = self.collection.find_one(query)
            return user_Data
        except:
            return None

    def read_user_global_history(self, user_id):
        try:
            query = {'_id': user_id}
            user_Data = self.collection.find_one(query)
            return user_Data
        except:
            return None

    def read_ranking_users_by_win(self):
        query = {'win_rank': {'$gt': 0}, '_id': {'$ne': '3goBRU', '$not': {'$regex': '^bot_'}}}
        selection_items = {"win_rank": 1}
        data = self.collection.find(query, selection_items).sort([('win_rank', pymongo.DESCENDING)]).limit(25)
        return data

    def update_user_history(self, user_id, incoming_data: dict):
        if str(user_id).startswith("bot_") or str(user_id).startswith("test_bot"):
            return None
        try:
            query = {'_id': user_id}
            inc_data = {}
            for key, val in incoming_data.items():
                if key in self.game_types or key in self.mode_keys:
                    inc_data[key] = int(val) if isinstance(val, (int, float)) else 1
            if inc_data:
                default_insert = {k: 0 for k in self.mode_keys if k not in inc_data}
                update_doc = {'$inc': inc_data}
                if default_insert:
                    update_doc['$setOnInsert'] = default_insert
                self.collection.find_one_and_update(query, update_doc, upsert=True)
        except Exception as e:
            print(f"[UserHistory] Error updating user history for {user_id}: {e}")

    def update_user_history_multiplayer(self, user_id, incoming_data: dict):
        return self.update_user_history(user_id, incoming_data)

    def delete_user_history(self, user_id):
        query = {'_id': user_id}
        self.collection.delete_one(query)

    def reset_users(self):
        remove_data = {}
        for game_type in self.game_types:
            remove_data[game_type] = 0
        reset_fields = {k: 0 for k in self.mode_keys}
        self.collection.update_many({}, {'$set': reset_fields, '$unset': remove_data})
