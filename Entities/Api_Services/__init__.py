import datetime

from fastapi import Header

from Commons.app_consts import admin_token
from Entities import Network_Exeptions


async def get_current_user(authorization: str = Header(...)):
    from Entities import Security
    from Entities import Network_Exeptions
    user_token_data = await Security.extract_token(authorization)
    if user_token_data is not None:
        from Entities.Database import game_database
        user = game_database.users_manager.read_user(user_token_data['id'])
        if user is None or user['device_id'] != user_token_data['device_id']:
            raise Network_Exeptions.raise401()
        else:
            return user
    else:
        raise Network_Exeptions.raise401()


def get_config():
    from Entities.Database import game_database
    return game_database.config_manager.read_config()


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
