from fastapi import APIRouter, Header, Depends, Form

from Entities.Api_Services import get_current_user

router = APIRouter(prefix='', tags=['general'])


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/config")
async def read_config():
    from Entities import Api_Services
    return {"result": Api_Services.get_config()}


@router.get("/classic-rank/config")
async def read_classic_rank_config():
    from Entities.Games.classic_rank_config import get_classic_rank_config
    return {"result": get_classic_rank_config()}


@router.get("/ranking-by-score")
async def func1():
    from Entities.Api_Services import user
    return {"result": user.get_ranking_users_by_score()}


@router.get("/ranking-by-win")
async def func2():
    from Entities.Api_Services import user
    return {"result": user.get_ranking_users_by_win()}


@router.get("/get-free-coin")
async def func2(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.get_free_coin(user_data['_id'], user_data['coin'], user_data['last_time_chance'])}


@router.post("/purchase")
async def say_hello(product_id: str = Form(...), market_type: str = Form(...), token: str = Form(...),
                    authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.purchase(user_data['_id'], product_id, market_type, token, user_data['coin'])}


@router.post("/redeem-promo")
async def redeem_promo_code(
    code: str = Form(...),
    authorization: str = Header(...),
    user_data=Depends(get_current_user),
):
    from Entities.Database import game_database
    result = game_database.promos_manager.redeem_code(
        user_id=str(user_data["_id"]),
        raw_code=code,
        users_collection=game_database.users_manager.collection,
    )
    return {"result": result}
