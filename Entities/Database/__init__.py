import pymongo

from Entities.Database.config_collection import ConfigCollectionManager
from Entities.Database.game_history_collection import GameHistoryCollectionManager
from Entities.Database.user_history_collection import UserHistoryCollectionManager
from Entities.Database.users_collection import UsersCollectionManager


class DataBaseManager:
    def __init__(self):
        self.db_client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.base_db = self.db_client["KafehFekrDB"]
        self.users_manager = UsersCollectionManager(self.base_db['users'])
        self.user_history_manager = UserHistoryCollectionManager(self.base_db['user_history'])
        self.game_history_manager = GameHistoryCollectionManager(self.base_db['game_history'])
        self.config_manager = ConfigCollectionManager(self.base_db['config'])


game_database = DataBaseManager()
# print(game_database.users_manager.read_users(["0","1"]))
# print(game_database.users_manager.create_user("9377804649", "Erfan"))
# game_database.users_manager.update_user("K2dWiy", xp=120, score=100)

# game_database.user_history_manager.create_user_history("0")
# game_database.user_history_manager.create_user_history("1")
# print(game_database.user_history_manager.read_user_history(0))
# game_database.user_history_manager.update_user_history(0, {'tictactoe_win': 3, 'win': 1})

# # game_database.game_history_manager.create_game_history(0, 1, "tictactoe", "Rank")
# print(game_database.game_history_manager.read_game_history("Y6pl1xm"))
# game_database.game_history_manager.update_game_history("Y6pl1xm", 1)
# game_database.game_history_manager.delete_unfinished_games()

# game_database.config_manager.create_config()
# print(game_database.config_manager.read_config())
# game_database.config_manager.update_config(latest_version="1.0.0", allowed_version="0.2.3")
