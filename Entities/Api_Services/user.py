from datetime import datetime, timedelta

from Commons.app_consts import admin_token
from Entities import Network_Exeptions

import requests

bazaar_access_token = "WUj6PEdIjgtimymkY8b8HKOvociLod"


def user_histories(user_id):
    from Entities.Database import game_database
    from Entities.Database.user_history_collection import create_user_history_json
    data = game_database.user_history_manager.read_user_history(user_id)
    if not data:
        data = game_database.user_history_manager.create_user_history(user_id) or create_user_history_json(user_id)
    return data


def user_game_histories(user_id):
    from Entities.Database import game_database
    games = game_database.game_play_history_manager.read_user_games_histories(user_id, limit=50)
    user_id_str = str(user_id)
    result = []
    user_cache = {}

    for g in games:
        g_id = str(g.get('_id', ''))
        rounds = game_database.game_history_manager.read_rounds_by_game_play_id(g_id)
        formatted_rounds = []
        for r in rounds:
            r_date = r.get('date')
            formatted_rounds.append({
                "round_id": str(r.get('_id', '')),
                "game_type": str(r.get('game_type', '')),
                "winner_id": r.get('winner_id'),
                "winner_user_id": str(r.get('winner_user_id', '')),
                "date": r_date.isoformat() if hasattr(r_date, 'isoformat') else str(r_date or ''),
            })

        users_info = g.get('users_info', [])
        if not users_info:
            user_ids = g.get('user_ids', [])
            if not user_ids:
                user_ids = []
                for i in range(1, 5):
                    k = f'user{i}_id'
                    if k in g and g[k]:
                        user_ids.append(str(g[k]))
            users_info = []
            for uid in user_ids:
                uid_str = str(uid)
                if uid_str.startswith("bot_"):
                    users_info.append({
                        "user_id": uid_str,
                        "username": "ربات هوشمند",
                        "name": "ربات هوشمند",
                        "image": 1,
                        "score": 1000,
                        "level": 1,
                        "xp": 0,
                        "coins": 0,
                    })
                else:
                    if uid_str not in user_cache:
                        user_cache[uid_str] = game_database.users_manager.read_global_user_data(uid_str)
                    u_data = user_cache.get(uid_str)
                    if u_data:
                        users_info.append({
                            "user_id": uid_str,
                            "username": u_data.get("name", u_data.get("username", "بازیکن")),
                            "name": u_data.get("name", u_data.get("username", "بازیکن")),
                            "image": int(u_data.get("image", 0)),
                            "score": int(u_data.get("score", 0)),
                            "level": int(u_data.get("level", 1)),
                            "xp": int(u_data.get("xp", 0)),
                            "coins": int(u_data.get("coins", u_data.get("coin", 0))),
                        })
                    else:
                        users_info.append({
                            "user_id": uid_str,
                            "username": "بازیکن",
                            "name": "بازیکن",
                            "image": 0,
                            "score": 0,
                            "level": 1,
                            "xp": 0,
                            "coins": 0,
                        })

        user_scores = g.get('user_scores', [])
        if not user_scores:
            user_scores = []
            for i in range(1, len(users_info) + 1):
                k = f'user{i}_score'
                user_scores.append(int(g.get(k, 0)))

        winner_id = g.get('winner_id')
        if winner_id is None or winner_id == "":
            u1_score = int(g.get('user1_score', 0))
            u2_score = int(g.get('user2_score', 0))
            u1_id = str(g.get('user1_id', ''))
            u2_id = str(g.get('user2_id', ''))
            if u1_score > u2_score and u1_id:
                winner_id = u1_id
            elif u2_score > u1_score and u2_id:
                winner_id = u2_id
            elif u1_score == u2_score and (u1_score > 0 or g.get('is_finished')):
                winner_id = "0"
            else:
                winner_id = ""

        winner_id_str = str(winner_id)
        if not g.get('is_finished', False):
            my_result = "unfinished"
        elif winner_id_str == user_id_str:
            my_result = "win"
        elif winner_id_str == "0":
            my_result = "draw"
        elif winner_id_str != "":
            my_result = "lose"
        else:
            my_result = "unfinished"

        s_date = g.get('start_date')
        f_date = g.get('finish_date')

        result.append({
            "_id": g_id,
            "game_play_id": g_id,
            "game_types": g.get("game_types", []),
            "game_score_type": g.get("game_score_type", "Rank"),
            "is_finished": bool(g.get("is_finished", False)),
            "start_date": s_date.isoformat() if hasattr(s_date, 'isoformat') else str(s_date or ''),
            "finish_date": f_date.isoformat() if hasattr(f_date, 'isoformat') else str(f_date or ''),
            "winner_id": winner_id_str,
            "winner_list": g.get("winner_list", []),
            "user_scores": user_scores,
            "users_info": users_info,
            "rounds": formatted_rounds,
            "my_result": my_result,
        })
    return result


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
    from Entities.Database.user_history_collection import create_user_history_json
    data = game_database.user_history_manager.read_user_history(user_id)
    if not data:
        data = game_database.user_history_manager.create_user_history(user_id) or create_user_history_json(user_id)
    return data


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
