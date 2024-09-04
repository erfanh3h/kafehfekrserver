from fastapi import Header


async def get_current_user(authorization: str = Header(...)):
    from Entities import Security
    from Entities.Network_Exeptions import HttpExceptions
    user_token_data = await Security.extract_token(authorization)
    if user_token_data is not None:
        from Entities.Database import game_database
        user = game_database.users_manager.read_user(user_token_data['id'])
        return user
    else:
        raise HttpExceptions().raise401()
