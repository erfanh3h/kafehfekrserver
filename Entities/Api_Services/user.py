from datetime import datetime, timedelta

from Commons.app_consts import admin_token
from Entities import Network_Exeptions


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


def update_image(user_id, image, user_coin):
    if user_coin < 50:
        raise Network_Exeptions.raise422(details="سکه کافی نداری")
    else:
        from Entities.Database import game_database
        game_database.users_manager.update_user(user_id, image=image, coin=user_coin - 50)


def update_username(user_id, username, user_coin):
    if user_coin < 75:
        raise Network_Exeptions.raise422(details="سکه کافی نداری")
    else:
        from Entities.Database import game_database
        game_database.users_manager.update_user(user_id, username=username, coin=user_coin - 75)


def update_coin(user_id, coin):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, coin=coin)


def update_coin_by_admin(token, user_id, coin):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        from Entities.Database import game_database
        return game_database.users_manager.update_user(user_id, coin=coin)


def get_users_count(token):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        from Entities.Database import game_database
        return game_database.users_manager.get_count_of_users()


def get_free_coin(user_id, prev_coin, last_time_chance: datetime):
    possible_time = last_time_chance + timedelta(hours=8)
    if possible_time < datetime.now():
        from Commons.static_functions import get_random_coin
        from Entities.Database import game_database
        coin = get_random_coin()
        game_database.users_manager.update_user(user_id, coin=coin + prev_coin, last_time_chance=datetime.now())
        return coin
    else:
        raise Network_Exeptions.raise422(details="زمانش نرسیده")


def read_user_data(user_id):
    from Entities.Database import game_database
    return game_database.users_manager.read_global_user_data(user_id)


def read_user_history_data(user_id):
    from Entities.Database import game_database
    return game_database.user_history_manager.read_user_global_history(user_id)