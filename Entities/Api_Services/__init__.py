from fastapi import Header


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
