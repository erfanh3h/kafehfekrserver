def user_histories(user_id):
    from Entities.Database import game_database
    return game_database.user_history_manager.read_user_history(user_id)


def user_game_histories(user_id):
    from Entities.Database import game_database
    return game_database.game_history_manager.read_user_games_histories(user_id)


def get_ranking_users_by_score():
    from Entities.Database import game_database
    return list(game_database.users_manager.read_ranking_users_by_score())


def get_ranking_users_by_win():
    def find_index_by_id(users_data, user_id):
        i = 0
        for r_data in users_data:
            if r_data['_id'] == user_id:
                return i
            i += 1
        return 0

    from Entities.Database import game_database
    users_id = []
    history_data = game_database.user_history_manager.read_ranking_users_by_win()
    for data in game_database.user_history_manager.read_ranking_users_by_win():
        users_id.append(data['_id'])

    by_win_data = game_database.users_manager.read_ranking_users_by_win(users_id)
    result = []
    for index, data in enumerate(users_id):
        item_index = find_index_by_id(by_win_data, data)
        raw_data = {'user_data': by_win_data[item_index], 'win': history_data[index]['win_rank']}
        result.append(raw_data)
    return result


def update_image(user_id, image):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, image=image)
