from datetime import datetime


def create_game_history_json(game_id, game_play_id, user_idis, game_type, game_score_type, winner_id, users_info=None) -> dict:
    u_ids = [str(u) for u in user_idis] if isinstance(user_idis, (list, tuple)) else [str(user_idis)]
    winner_user_id = ""
    if isinstance(winner_id, int):
        if 0 < winner_id <= len(u_ids):
            winner_user_id = u_ids[winner_id - 1]
        elif winner_id == 0:
            winner_user_id = "0"
    elif winner_id is not None:
        winner_user_id = str(winner_id)

    data = {
        '_id': str(game_id),
        'game_play_id': str(game_play_id),
        'user_ids': u_ids,
        'winner_id': winner_id,
        'winner_user_id': winner_user_id,
        'game_type': str(game_type),
        'game_score_type': str(game_score_type),
        'date': datetime.now(),
        'users_info': users_info or [],
        'is_finished': True,
    }
    for index, user_id in enumerate(u_ids):
        data[f'user{index + 1}_id'] = user_id
    return data


class GameHistoryCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def create_game_history(self, game_id, game_play_id, user_idis, game_type, game_score_type, winner_id, users_info=None):
        game_data = create_game_history_json(game_id, game_play_id, user_idis, game_type, game_score_type, winner_id, users_info=users_info)
        self.collection.insert_one(game_data)
        return game_data

    def read_game_history(self, game_id):
        try:
            query = {'_id': str(game_id)}
            game_Data = self.collection.find_one(query)
            return game_Data
        except Exception:
            return None

    def read_rounds_by_game_play_id(self, game_play_id):
        try:
            return list(self.collection.find({'game_play_id': str(game_play_id)}).sort('date', 1))
        except Exception:
            return []

    def read_user_games_histories(self, user_id):
        result = []
        try:
            uid = str(user_id)
            query = {
                '$or': [
                    {'user_ids': uid},
                    {'user1_id': uid},
                    {'user2_id': uid},
                    {'user3_id': uid},
                    {'user4_id': uid},
                ]
            }
            cursor = self.collection.find(query).sort('date', -1)
            for item in cursor:
                result.append(item)
        except Exception:
            pass
        return result

    def update_game_history(self, game_id, winner_id):
        try:
            query = {'_id': str(game_id)}
            update_data = {"date": datetime.now(), "winner_id": winner_id}
            self.collection.find_one_and_update(query, {'$set': update_data})
        except Exception:
            pass

    def delete_game_history(self, game_id):
        try:
            query = {'_id': str(game_id)}
            self.collection.delete_one(query)
        except Exception:
            pass

    def delete_unfinished_games(self):
        query = {'is_finished': False}
        self.collection.delete_many(query)

    def get_count_of_unfinished_games(self):
        return self.collection.count_documents({'is_finished': False})

    def get_count_of_finished_games(self):
        return self.collection.count_documents({'is_finished': True})

    def reset_data(self):
        self.collection.delete_many({})
