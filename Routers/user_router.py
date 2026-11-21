from fastapi import APIRouter, Form, Header, Depends

from Entities.Api_Services import get_current_user

router = APIRouter(prefix='', tags=['user'])


@router.post("/check_match_allow")
async def check_match_allow(version: str = Form(""), authorization: str = Header(...), user=Depends(get_current_user)):
    from Entities import Api_Services, Network_Exeptions
    from Commons.static_functions import is_version_allowed
    config_data = Api_Services.get_config() or {}
    allowed_ver = str(config_data.get("allowed_version", "2.0.0")).strip()
    latest_ver = str(config_data.get("latest_version", "2.0.0")).strip()
    is_queue_open = bool(config_data.get("is_queue_open", True))

    if version and allowed_ver and not is_version_allowed(version, allowed_ver):
        raise Network_Exeptions.raise403(details=f"نسخه برنامه شما ({version}) قدیمی است. لطفاً برای بازی، برنامه را به نسخه {allowed_ver} به‌روزرسانی کنید.")

    if not is_queue_open:
        raise Network_Exeptions.raise403(details="صف ورود به بازی موقتاً توسط مدیریت بسته شده است.")

    return {
        "result": True,
        "allowed_version": allowed_ver,
        "latest_version": latest_ver,
        "is_queue_open": is_queue_open,
    }


@router.get("/my-data")
async def my_data(authorization: str = Header(default=""), user=Depends(get_current_user)):
    return {"result": user}


@router.get("/history")
@router.get("/my-history")
async def get_user_history_endpoint(authorization: str = Header(default=""), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.user_histories(user_data['_id'])}


@router.get("/game-history")
@router.get("/my-game-history")
async def get_user_game_history_endpoint(authorization: str = Header(default=""), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.user_game_histories(user_data['_id'])}


@router.get("/user-data/{user_id}")
async def say_hello(user_id: str):
    from Entities.Api_Services import user
    data = user.read_user_data(user_id)
    history_data = user.read_user_history_data(user_id)
    return {"result": {'data': data, 'history': history_data}}


@router.post("/update-image")
async def say_hello(image: int = Form(...), authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    user.update_image(user_data['_id'], image, user_data['coin'], user_data['image'])
    return {"result": True}


@router.post("/update-frame")
async def update_user_frame(frame: int = Form(...), authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    saved_frame = user.update_frame(user_data['_id'], frame)
    return {"result": True, "frame": saved_frame}


@router.post("/update-username")
async def say_hello(username: str = Form(...), authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    user.update_username(user_data['_id'], username, user_data['coin'])
    return {"result": True}
