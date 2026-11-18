def check_not_in_game(user_phone):
    from Entities.Database import game_database
    from Entities.Api_Services.social import realtime_bridge
    user_data = game_database.users_manager.read_user_by_phone(user_phone)
    if user_data is None:
        return True
    uid = str(user_data.get("_id", "") or "")
    # 1. Authoritative check against realtime backend RAM games
    rt_in_game = realtime_bridge.check_user_in_game_realtime(uid)
    if rt_in_game is True:
        return False
    if rt_in_game is False:
        # Clear stale open_game_id if backend confirms no active match
        if user_data.get("open_game_id", ""):
            try:
                game_database.users_manager.update_user(uid, open_game_id="")
            except Exception:
                pass
        return True
    # 2. Fallback when realtime backend is unreachable: inspect open_game_id + unfinished history doc
    open_gid = str(user_data.get("open_game_id", "") or "").strip()
    if open_gid:
        try:
            g_doc = game_database.game_play_history_manager.read_game_play_history(open_gid)
            if isinstance(g_doc, dict) and g_doc.get("is_finished") is True:
                game_database.users_manager.update_user(uid, open_game_id="")
                return True
        except Exception:
            pass
        return False
    return True


def enter_user(user_phone, device_id):
    from Entities.Database import game_database
    user_data, is_new_user = game_database.users_manager.create_user(phone=user_phone, device_id=device_id)
    if is_new_user:
        if user_data is not None:
            game_database.user_history_manager.create_user_history(user_data['_id'])
    elif user_data is not None:
        game_database.users_manager.update_user(user_data['_id'], device_id=device_id)

    return user_data


def complete_user(user_id, username, rep_id):
    from Entities.Database import game_database
    game_database.users_manager.update_user(user_id, username=username)
    if rep_id != "":
        rep_user = game_database.users_manager.read_user(rep_id)
        if rep_user is not None:
            game_database.users_manager.update_user(rep_id, coin=rep_user['coin'] + 30)
