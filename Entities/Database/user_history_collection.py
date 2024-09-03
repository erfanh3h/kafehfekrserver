from Entities.Games.game_types import GameTypesEnum


def create_user_history_json(user_id) -> dict:
    result = {'_id': user_id, "win": 0, "draw": 0, "lose": 0}
    return result


class UserHistoryCollectionManager:
    def __init__(self, collection):
        self.collection = collection
        self.game_types: list[str] = []
        for game_type in [game.value for game in GameTypesEnum]:
            self.game_types.append(f'{game_type.lower()}_win')
            self.game_types.append(f'{game_type.lower()}_draw')
            self.game_types.append(f'{game_type.lower()}_lose')

    def create_user_history(self, user_id):
        user_data = create_user_history_json(user_id)
        self.collection.insert_one(user_data)
        return user_data

    def read_user_history(self, user_id):
        try:
            query = {'_id': user_id}
            user_Data = self.collection.find_one(query)
            return user_Data
        except:
            return None

    def update_user_history(self, user_id, incoming_data: dict):
        try:
            query = {'_id': user_id}
            update_data = {}
            user_data = self.read_user_history(user_id)
            for key in incoming_data.keys():
                if self.game_types.__contains__(key) or ["win", "draw", "lose"].__contains__(key):
                    # check prevoisly data was added
                    if user_data.keys().__contains__(key):
                        update_data[key] = incoming_data[key] + user_data[key]
                    else:
                        update_data[key] = incoming_data[key]
            self.collection.find_one_and_update(query, {'$set': update_data})
        except:
            pass

    def delete_user_history(self, user_id):
        query = {'_id': user_id}
        self.collection.delete_one(query)
