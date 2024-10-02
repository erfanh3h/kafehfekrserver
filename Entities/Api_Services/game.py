from Commons.app_consts import admin_token
from Entities import Network_Exeptions


def get_unfinished_games(token):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        from Entities.Database import game_database
        return game_database.game_play_history_manager.get_count_of_unfinished_games()


def get_finished_games(token):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        from Entities.Database import game_database
        return game_database.game_play_history_manager.get_count_of_finished_games()


def delete_unfinished_games(token):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        from Entities.Database import game_database
        game_database.game_play_history_manager.delete_unfinished_games()
        game_database.users_manager.reset_all_users_active_games()
        return True
