def check_not_in_game(user_phone):
    from Entities.Database import game_database
    user_data = game_database.users_manager.read_user_by_phone(user_phone)
    if user_data is not None:
        if user_data['open_game_id'] != "":
            return False
    return True


def enter_user(user_phone, device_id):
    from Entities.Database import game_database
    user_data, is_new_user = game_database.users_manager.create_user(phone=user_phone, device_id=device_id)
    if is_new_user:
        game_database.user_history_manager.create_user_history(user_data['_id'])
    else:
        game_database.users_manager.update_user(user_data['_id'], device_id=device_id)

    return user_data


def complete_user(user_id, username):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, username=username)
