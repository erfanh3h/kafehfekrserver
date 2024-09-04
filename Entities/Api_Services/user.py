def user_histories(user_id):
    from Entities.Database import game_database
    return game_database.user_history_manager.read_user_history(user_id)


def user_game_histories(user_id):
    from Entities.Database import game_database
    return game_database.game_history_manager.read_user_games_histories(user_id)
