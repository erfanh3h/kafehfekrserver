from fastapi import APIRouter

router = APIRouter(prefix='/admin', tags=['auth'])


@router.get("/unfinished-games")
async def func1(token: str):
    from Entities.Api_Services import game
    return {"result": game.get_unfinished_games(token)}


@router.get("/delete-unfinished-games")
async def func2(token: str):
    from Entities.Api_Services import game
    return {"result": game.delete_unfinished_games(token)}


@router.get("/config-let-queue")
async def func3(token: str, value: bool, hour: int, minute: int):
    from Entities.Api_Services import set_config_let_queue
    set_config_let_queue(token, value, hour, minute)
    return {"result": value}


@router.get("/change-version")
async def func4(token: str, allowed, latest):
    from Entities.Api_Services import change_version
    change_version(token, allowed, latest)
    return {"result": [allowed, latest]}
