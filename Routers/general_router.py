from fastapi import APIRouter, Header, Depends

from Entities.Api_Services import get_current_user

router = APIRouter(prefix='', tags=['general'])


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/config")
async def read_config():
    from Entities import Api_Services
    return {"result": Api_Services.get_config()}


@router.get("/ranking-by-score")
async def func1(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.get_ranking_users_by_score()}


@router.get("/ranking-by-win")
async def func2(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.get_ranking_users_by_win()}
