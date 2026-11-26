import datetime

from fastapi import Header

from Commons.app_consts import admin_token
from Entities import Network_Exeptions


async def get_current_user(authorization: str = Header(default="")):
    from Entities import Security
    from Entities import Network_Exeptions
    from Commons.static_functions import check_ban_and_auto_unban
    if not authorization or authorization.strip() in ("", "null", "undefined"):
        raise Network_Exeptions.raise401()
    user_token_data = await Security.extract_token(authorization)
    if user_token_data is None:
        raise Network_Exeptions.raise401()
    from Entities.Database import game_database
    user = game_database.users_manager.read_user(user_token_data['id'])
    if user is None or user.get('device_id') != user_token_data.get('device_id'):
        raise Network_Exeptions.raise401()
    if check_ban_and_auto_unban(user, game_database.users_manager):
        raise Network_Exeptions.raise403(details="حساب کاربری شما توسط مدیریت مسدود شده است.")
    else:
        return user


async def get_current_user_optional(authorization: str = Header(default="")):
    if not authorization or authorization.strip() in ("", "null", "undefined"):
        return None
    try:
        from Entities import Security
        from Commons.static_functions import check_ban_and_auto_unban
        user_token_data = await Security.extract_token(authorization)
        if user_token_data is None:
            return None
        from Entities.Database import game_database
        user = game_database.users_manager.read_user(user_token_data['id'])
        if user is None or user.get('device_id') != user_token_data.get('device_id'):
            return None
        if check_ban_and_auto_unban(user, game_database.users_manager):
            return None
        return user
    except Exception:
        return None


def get_config():
    from Entities.Database import game_database
    from Entities.Games.classic_rank_config import get_classic_rank_config
    cfg = game_database.config_manager.read_config()
    result = dict(cfg) if isinstance(cfg, dict) else {}
    result["classic_rank_config"] = get_classic_rank_config()
    return result


def set_config_let_queue(token, value: bool, hour: int, minute: int):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        current_date = datetime.datetime.now()
        from Entities.Database import game_database
        return game_database.config_manager.update_config(is_queue_open=value,
                                                          update_finish_date=datetime.datetime(current_date.year,
                                                                                               current_date.month,
                                                                                               current_date.day, hour,
                                                                                               minute))


def change_version(token, allowed, latest):
    if token != admin_token:
        raise Network_Exeptions.raise401()
    else:
        from Entities.Database import game_database
        return game_database.config_manager.update_config(latest_version=latest, allowed_version=allowed)


def reset_databases():
    from Entities.Database import game_database
    game_database.users_manager.reset_users()
    game_database.users_manager.reset_coins()
    game_database.user_history_manager.reset_users()
    game_database.game_history_manager.reset_data()
