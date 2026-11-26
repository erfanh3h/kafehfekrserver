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

    # Batch-load rounds for all games in one query instead of N+1 queries
    game_ids = [str(g.get('_id', '')) for g in games if g.get('_id')]
    if hasattr(game_database.game_history_manager, "read_rounds_by_game_play_ids"):
        rounds_by_game = game_database.game_history_manager.read_rounds_by_game_play_ids(game_ids)
    else:
        rounds_by_game = {gid: game_database.game_history_manager.read_rounds_by_game_play_id(gid) for gid in game_ids}

    # Batch-preload any user IDs needed for legacy documents lacking embedded users_info
    missing_uids = []
    for g in games:
        if not g.get('users_info'):
            uids = g.get('user_ids') or [g.get(f'user{i}_id') for i in range(1, 5) if g.get(f'user{i}_id')]
            for uid in uids:
                uid_s = str(uid)
                if uid_s and not uid_s.startswith("bot_") and uid_s not in user_cache:
                    user_cache[uid_s] = None
                    missing_uids.append(uid_s)
    if missing_uids and hasattr(game_database.users_manager, "read_users"):
        try:
            for u_doc in game_database.users_manager.read_users(missing_uids):
                if u_doc and "_id" in u_doc:
                    user_cache[str(u_doc["_id"])] = u_doc
        except Exception:
            pass

    for g in games:
        g_id = str(g.get('_id', ''))
        rounds = rounds_by_game.get(g_id, [])
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

        raw_ai_level = g.get('ai_level')
        ai_level_val = int(raw_ai_level) if raw_ai_level in (1, 2, 3, "1", "2", "3") else None
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
                        "level": ai_level_val or 2,
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
                            "profile_frame": int(u_data.get("profile_frame", 0)),
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
                            "profile_frame": 0,
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

        winner_list = g.get('winner_list', []) or []
        winner_id = g.get('winner_id')
        if winner_id is None or winner_id == "":
            if winner_list:
                winner_id = str(winner_list[0])
            elif len(users_info) > 2 and user_scores:
                max_sc = max(user_scores)
                if max_sc > 0:
                    top_idxs = [i for i, sc in enumerate(user_scores) if sc == max_sc]
                    if len(top_idxs) == 1 and top_idxs[0] < len(users_info):
                        winner_id = str(users_info[top_idxs[0]].get("user_id", ""))
                    else:
                        winner_id = "0"
                else:
                    winner_id = ""
            else:
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

        # Convenient top-level opponent extraction
        opp_name = "حریف"
        opp_img = 0
        opp_id = ""
        for u in users_info:
            if str(u.get("user_id", "")) != user_id_str:
                opp_name = str(u.get("username", u.get("name", "حریف")))
                opp_img = int(u.get("image", 0))
                opp_id = str(u.get("user_id", ""))
                break
        first_game = g.get("game_types", ["بازی"])[0] if g.get("game_types") else "بازی"

        result.append({
            "_id": g_id,
            "game_play_id": g_id,
            "user1_id": str(g.get("user1_id", users_info[0].get("user_id", "") if users_info else "")),
            "game_types": g.get("game_types", []),
            "game_type": first_game,
            "game_score_type": g.get("game_score_type", "Rank"),
            "ai_level": ai_level_val,
            "is_finished": bool(g.get("is_finished", False)),
            "start_date": s_date.isoformat() if hasattr(s_date, 'isoformat') else str(s_date or ''),
            "finish_date": f_date.isoformat() if hasattr(f_date, 'isoformat') else str(f_date or ''),
            "winner_id": winner_id_str,
            "winner": winner_id_str,
            "winner_list": winner_list,
            "user_scores": user_scores,
            "users_info": users_info,
            "opponent_name": opp_name,
            "opponent_image": opp_img,
            "opponent_id": opp_id,
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
            u_info = by_win_map[uid]
            raw_data = {
                '_id': uid,
                'user_id': uid,
                'username': u_info.get('username', 'بازیکن'),
                'name': u_info.get('username', 'بازیکن'),
                'image': int(u_info.get('image', 0)),
                'score': int(u_info.get('score', 0)),
                'win': int(h.get('win_rank', 0)),
                'user_data': u_info
            }
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


def update_frame(user_id, frame):
    from Entities.Database import game_database
    f_clamped = max(1, min(20, int(frame)))
    game_database.users_manager.update_user(user_id, profile_frame=f_clamped, avatar_frame=f_clamped)
    return f_clamped


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


def get_free_coin(user_id, prev_coin, last_time_chance: datetime | None):
    now = datetime.now()
    cutoff = now - timedelta(hours=8)
    if isinstance(last_time_chance, datetime) and last_time_chance >= cutoff:
        raise Network_Exeptions.raise422(details="زمانش نرسیده")

    from Commons.static_functions import get_random_coin
    from Entities.Database import game_database
    coin = get_random_coin()
    col = getattr(game_database.users_manager, "collection", None)
    if col is not None and hasattr(col, "find_one_and_update"):
        updated = col.find_one_and_update(
            {
                "_id": user_id,
                "$or": [
                    {"last_time_chance": {"$lt": cutoff}},
                    {"last_time_chance": {"$exists": False}},
                    {"last_time_chance": None},
                ],
            },
            {"$inc": {"coin": coin}, "$set": {"last_time_chance": now}},
        )
        if updated is None:
            raise Network_Exeptions.raise422(details="زمانش نرسیده")
    else:
        game_database.users_manager.update_user(user_id, coin=coin + (prev_coin or 0), last_time_chance=now)
    return coin


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


_PRODUCT_COIN_AMOUNTS = {
    "1": 50,
    "2": 160,
    "3": 330,
    "4": 525,
    "5": 1100,
    "6": 1700,
}


def get_new_bazaar_token() -> bool:
    global bazaar_access_token
    url = 'https://pardakht.cafebazaar.ir/devapi/v2/auth/token/'
    data = {'grant_type': "refresh_token", "client_id": "kaBZZL25bFEn8HhvdplDbARwIkg62TIokTv0koVu",
            "client_secret": "sucwTiAKMFcwbNlVIshe9zGtF1CYKZH3pz5n4kYoX4TIKAt0G7keypcEvYLV",
            "refresh_token": "RIBu8CaRQFjOeRdv1CHSaFEEGXwgP3"}
    try:
        req = requests.post(url, json=data, timeout=8)
        payload = req.json()
        if isinstance(payload, dict) and payload.get('access_token'):
            bazaar_access_token = payload['access_token']
            return True
    except Exception:
        pass
    return False


def purchase(user_id, product_id, market_type, token, prev_coin, _retried: bool = False):
    tok = str(token or "").strip()
    if not tok:
        return False
    from Entities.Database import game_database
    if hasattr(game_database.purchase_manager, "has_purchase_token") and game_database.purchase_manager.has_purchase_token(market_type, tok):
        return False

    is_token_true = False
    if market_type == "Myket":
        url = f'https://developer.myket.ir/api/partners/applications/kafeh.fekr.classic/purchases/products/{product_id}/verify'
        data = {'tokenId': tok}
        header = {'X-Access-Token': "fb9aa38c-47f0-41d6-924b-ac712e553e5e"}
        try:
            req = requests.post(url, json=data, headers=header, timeout=8)
            payload = req.json()
            is_token_true = isinstance(payload, dict) and ('developerPayload' in payload)
        except Exception:
            is_token_true = False
    else:
        url = f'https://pardakht.cafebazaar.ir/devapi/v2/api/validate/kafeh.fekr.classic/inapp/{product_id}/purchases/{tok}/?access_token={bazaar_access_token}'
        try:
            req = requests.post(url, timeout=8)
            if req.status_code == 401 and not _retried:
                if get_new_bazaar_token():
                    return purchase(user_id, product_id, market_type, tok, prev_coin, _retried=True)
                return False
            payload = req.json()
            is_token_true = isinstance(payload, dict) and ("error" not in payload)
        except Exception:
            if not _retried and get_new_bazaar_token():
                return purchase(user_id, product_id, market_type, tok, prev_coin, _retried=True)
            is_token_true = False

    if is_token_true:
        added_coins = _PRODUCT_COIN_AMOUNTS.get(str(product_id), 0)
        if added_coins > 0:
            col = getattr(game_database.users_manager, "collection", None)
            if col is not None and hasattr(col, "find_one_and_update"):
                col.find_one_and_update({"_id": user_id}, {"$inc": {"coin": added_coins}})
            else:
                game_database.users_manager.update_user(user_id, coin=added_coins + (prev_coin or 0))
        game_database.purchase_manager.create_purchase(user_id, product_id, market_type, tok)
        return True
    return False
