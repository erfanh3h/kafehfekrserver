from datetime import datetime


def create_game_play_history_json(game_play_id, user_idis, game_types, game_score_type, users_info=None) -> dict:
    u_ids = [str(u) for u in user_idis] if isinstance(user_idis, (list, tuple)) else [str(user_idis)]
    create_dict = {
        '_id': str(game_play_id),
        'user_ids': u_ids,
        'game_types': list(game_types) if isinstance(game_types, (list, tuple)) else [str(game_types)],
        'game_score_type': str(game_score_type),
        'is_finished': False,
        'start_date': datetime.now(),
        'users_info': users_info or [],
        'winner_id': "",
        'winner_list': [],
        'user_scores': [],
    }
    for index, user_id in enumerate(u_ids):
        create_dict[f'user{index + 1}_id'] = user_id
    return create_dict


class GamePlayHistoryCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def create_game_play_history(self, game_play_id, user_idis, game_types, game_score_type, users_info=None):
        game_data = create_game_play_history_json(game_play_id, user_idis, game_types, game_score_type, users_info=users_info)
        self.collection.insert_one(game_data)
        return game_data

    def read_game_play_history(self, game_id):
        try:
            query = {'_id': str(game_id)}
            game_Data = self.collection.find_one(query)
            return game_Data
        except Exception:
            return None

    def read_user_games_histories(self, user_id, limit=50):
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
            cursor = self.collection.find(query).sort([('start_date', -1), ('_id', -1)]).limit(limit)
            return list(cursor)
        except Exception as e:
            print(f"[GamePlayHistory] Error reading user history: {e}")
            return []

    def update_game_play_history(self, game_id, winner_list, user_scores, winner_id=None):
        try:
            query = {'_id': str(game_id)}
            now = datetime.now()
            scores = list(user_scores) if isinstance(user_scores, (list, tuple)) else []
            update_data = {
                "finish_date": now,
                "is_finished": True,
                "winner_list": list(winner_list) if isinstance(winner_list, (list, tuple)) else [],
                "user_scores": scores,
            }
            if winner_id is not None:
                update_data["winner_id"] = str(winner_id)
            for index, user_score in enumerate(scores):
                update_data[f'user{index + 1}_score'] = user_score
            self.collection.find_one_and_update(query, {'$set': update_data})
        except Exception as e:
            print(f"[GamePlayHistory] Error updating: {e}")

    def delete_game_play_history(self, game_id):
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
