from fastapi import APIRouter, Depends, Header

from Entities.Api_Services import get_current_user, get_current_user_optional
from Entities.Api_Services.social import spectator

router = APIRouter(prefix="/spectator", tags=["spectator"])


@router.get("/live-games")
async def get_live_spectatable_games_endpoint(
    game_type: str = "",
    player_id: str = "",
    clan_id: str = "",
    visibility: str = "all",
    filter: str = "",
    filter_scope: str = "",
    page: int = 1,
    limit: int = 20,
    authorization: str = Header(default=""),
    user=Depends(get_current_user_optional),
):
    effective_filter = filter_scope or filter or visibility
    viewer_id = str(user["_id"]) if user and isinstance(user, dict) else ""
    return {
        "status": "success",
        "result": spectator.list_live_spectatable_games(
            viewer_id=viewer_id,
            game_type=game_type,
            player_id=player_id,
            clan_id=clan_id,
            visibility_filter=effective_filter,
            page=page,
            limit=limit,
        ),
    }


@router.get("/live-games/{game_id}")
async def get_live_spectator_game_detail_endpoint(
    game_id: str,
    authorization: str = Header(default=""),
    user=Depends(get_current_user_optional),
):
    viewer_id = str(user["_id"]) if user and isinstance(user, dict) else ""
    return {
        "status": "success",
        "result": spectator.get_live_game_summary(viewer_id=viewer_id, game_id=game_id),
    }

