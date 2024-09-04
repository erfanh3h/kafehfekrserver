def user_histories(user_id):
    from Entities.Database import game_database
    return game_database.user_history_manager.read_user_history(user_id)


def user_game_histories(user_id):
    from Entities.Database import game_database
    return game_database.game_history_manager.read_user_games_histories(user_id)


def update_image(user_id, image):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, image=image)
