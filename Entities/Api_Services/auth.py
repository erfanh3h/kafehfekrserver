def check_not_in_game(user_phone):
    from Entities.Database import game_database
    user_data = game_database.users_manager.read_user_by_phone(user_phone)
    if user_data is not None:
        if user_data['open_game_id'] != "":
            return False
    return True


def enter_user(user_phone):
    from Entities.Database import game_database
    return game_database.users_manager.create_user(phone=user_phone)


def complete_user(user_id, username, device_id):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, username=username, device_id=device_id)
