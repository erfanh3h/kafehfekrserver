from Entities.Database.social import (
    FriendsCollectionManager,
    ClansCollectionManager,
    ClanMessagesCollectionManager,
    DirectMessagesCollectionManager,
    NotificationsCollectionManager,
    InvitationsCollectionManager,
    ReportsCollectionManager,
    PresenceCollectionManager,
)
import os
import pymongo

from Entities.Database.config_collection import ConfigCollectionManager
from Entities.Database.game_history_collection import GameHistoryCollectionManager
from Entities.Database.game_play_history_collection import GamePlayHistoryCollectionManager
from Entities.Database.purchases_collection import PurchasesCollectionManager
from Entities.Database.user_history_collection import UserHistoryCollectionManager
from Entities.Database.users_collection import UsersCollectionManager


class DataBaseManager:
    def __init__(self):
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.db_client = pymongo.MongoClient(mongo_uri)
        self.base_db = self.db_client["KafehFekrDB"]
        self.users_manager = UsersCollectionManager(self.base_db['users'])
        self.user_history_manager = UserHistoryCollectionManager(self.base_db['user_history'])
        self.game_play_history_manager = GamePlayHistoryCollectionManager(self.base_db['game_play_history'])
        self.game_history_manager = GameHistoryCollectionManager(self.base_db['game_history'])
        self.purchase_manager = PurchasesCollectionManager(self.base_db['purchases'])
        self.config_manager = ConfigCollectionManager(self.base_db['config'])
        self.friends_manager = FriendsCollectionManager(
            self.base_db["friendships"],
            self.base_db["friend_requests"],
            self.base_db["user_blocks"],
        )
        self.clans_manager = ClansCollectionManager(
            self.base_db["clans"],
            self.base_db["clan_members"],
            self.base_db["clan_join_requests"],
            self.base_db["clan_invitations"],
            self.base_db["clan_challenges"],
            self.base_db["clan_audit_logs"],
        )
        self.clan_messages_manager = ClanMessagesCollectionManager(self.base_db["clan_messages"])
        self.direct_messages_manager = DirectMessagesCollectionManager(
            self.base_db["direct_conversations"],
            self.base_db["direct_messages"],
        )
        self.notifications_manager = NotificationsCollectionManager(
            self.base_db["social_notifications"],
            self.base_db["notification_preferences"],
        )
        self.invitations_manager = InvitationsCollectionManager(self.base_db["game_invitations"])
        self.reports_manager = ReportsCollectionManager(self.base_db["social_reports"])
        self.presence_manager = PresenceCollectionManager(self.base_db["user_presence"])


    def check_create_collections(self):
        if not self.db_client.list_database_names().__contains__("KafehFekrDB"):
            user_data, is_created = self.users_manager.create_user("9377804649", "Erfan")
            self.user_history_manager.create_user_history(user_data['_id'])
            self.game_play_history_manager.create_game_play_history("1", "1", "2", ["TicTacToe"], "Normal")
            self.game_history_manager.create_game_history("0", "1", "1", "2",
                                                          "TicTacToe", "Normal", "1")
            self.purchase_manager.create_purchase("1", "1", "bazaar", "t")
            self.config_manager.create_config()


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
