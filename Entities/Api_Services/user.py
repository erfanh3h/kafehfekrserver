from datetime import datetime, timedelta

from Commons.app_consts import admin_token
from Entities import Network_Exeptions

import requests

bazaar_access_token = "WUj6PEdIjgtimymkY8b8HKOvociLod"


def user_histories(user_id):
    from Entities.Database import game_database
    return game_database.user_history_manager.read_user_history(user_id)


def user_game_histories(user_id):
    from Entities.Database import game_database
    return game_database.game_play_history_manager.read_user_games_histories(user_id)


def get_ranking_users_by_score():
    from Entities.Database import game_database
    return list(game_database.users_manager.read_ranking_users_by_score())


def get_ranking_users_by_win():
    from Entities.Database import game_database
    history_data = list(game_database.user_history_manager.read_ranking_users_by_win())
    users_id = [data['_id'] for data in history_data if not (str(data['_id']).startswith("bot_") or str(data['_id']).startswith("test_bot"))]

    by_win_data = game_database.users_manager.read_ranking_users_by_win(users_id)
    by_win_map = {str(u['_id']): u for u in by_win_data}
    result = []
    for h in history_data:
        uid = str(h['_id'])
        if uid in by_win_map:
            raw_data = {'user_data': by_win_map[uid], 'win': h.get('win_rank', 0)}
            result.append(raw_data)
    return result


def update_image(user_id, image, user_coin, prev_image):
    #TODO : coin removed temporary
    # if user_coin < 50 and prev_image != 0:
    #     raise Network_Exeptions.raise422(details="سکه کافی نداری")
    # else:
    from Entities.Database import game_database
    if prev_image == 0:
        game_database.users_manager.update_user(user_id, image=image, coin=user_coin)
    else:
        game_database.users_manager.update_user(user_id, image=image, coin=user_coin - 50)


def update_username(user_id, username, user_coin):
    #TODO : coin removed temporary
    # if user_coin < 75:
    #     raise Network_Exeptions.raise422(details="سکه کافی نداری")
    # else:
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


def get_new_bazaar_token():
    global bazaar_access_token
    url = 'https://pardakht.cafebazaar.ir/devapi/v2/auth/token/'
    data = {'grant_type': "refresh_token", "client_id": "kaBZZL25bFEn8HhvdplDbARwIkg62TIokTv0koVu",
            "client_secret": "sucwTiAKMFcwbNlVIshe9zGtF1CYKZH3pz5n4kYoX4TIKAt0G7keypcEvYLV",
            "refresh_token": "RIBu8CaRQFjOeRdv1CHSaFEEGXwgP3"}
    req = requests.post(url, json=data)
    try:
        bazaar_access_token = req.json()['access_token']
    except:
        pass


def purchase(user_id, product_id, market_type, token, prev_coin):
    if market_type == "Myket":
        url = f'https://developer.myket.ir/api/partners/applications/kafeh.fekr.classic/purchases/products/{product_id}/verify'
        data = {'tokenId': token}
        header = {'X-Access-Token': "fb9aa38c-47f0-41d6-924b-ac712e553e5e"}
        req = requests.post(url, json=data, headers=header)
        try:
            payload = req.json()['developerPayload']
            is_token_true = True
        except:
            is_token_true = False
    else:
        url = f'https://pardakht.cafebazaar.ir/devapi/v2/api/validate/kafeh.fekr.classic/inapp/{product_id}/purchases/{token}/?access_token={bazaar_access_token}'
        req = requests.post(url)
        {}.keys().__contains__("error")
        try:
            payload = req.json()
            if payload.keys().__contains__("error"):
                is_token_true = False
            else:
                is_token_true = True
        except:
            get_new_bazaar_token()
            return purchase(user_id, product_id, market_type, token, prev_coin)
    if is_token_true:
        from Entities.Database import game_database
        if product_id == "1":
            coin = 50 + prev_coin
        elif product_id == "2":
            coin = 160 + prev_coin
        elif product_id == "3":
            coin = 330 + prev_coin
        elif product_id == "4":
            coin = 525 + prev_coin
        elif product_id == "5":
            coin = 1100 + prev_coin
        elif product_id == "6":
            coin = 1700 + prev_coin
        else:
            coin = prev_coin
        game_database.users_manager.update_user(user_id, coin=coin)
        game_database.purchase_manager.create_purchase(user_id, product_id, market_type, token)
        return True
    return False
