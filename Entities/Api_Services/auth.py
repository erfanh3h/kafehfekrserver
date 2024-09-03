def enter_user(user_phone):
    from Entities.Database import game_database
    return game_database.users_manager.create_user(phone=user_phone)


def complete_user(user_id, username, device_id):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, username=username, device_id=device_id)
