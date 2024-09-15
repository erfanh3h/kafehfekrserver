from fastapi import APIRouter, Form, Header, Depends

from Entities.Api_Services import get_current_user

router = APIRouter(prefix='', tags=['user'])


@router.post("/check_match_allow")
async def check_match_allow(version: str, authorization: str = Header(...), user=Depends(get_current_user)):
    from Entities import Api_Services
    config_data = Api_Services.get_config()
    return {"result": True}


@router.get("/my-data")
async def my_data(authorization: str = Header(...), user=Depends(get_current_user)):
    return {"result": user}


@router.get("/my-history")
async def say_hello(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.user_histories(user_data['_id'])}


@router.get("/my-game-history")
async def say_hello(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.user_game_histories(user_data['_id'])}


@router.get("/user-data/{user_id}")
async def say_hello(user_id: str, authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    data = user.read_user_data(user_id)
    history_data = user.read_user_history_data(user_id)
    return {"result": {'data': data, 'history': history_data}}


@router.post("/update-image")
async def say_hello(image: int = Form(...), authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    user.update_image(user_data['_id'], image, user_data['coin'])
    return {"result": True}


@router.post("/update-username")
async def say_hello(username: str = Form(...), authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    user.update_username(user_data['_id'], username, user_data['coin'])
    return {"result": True}
