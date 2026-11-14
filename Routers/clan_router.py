from fastapi import APIRouter, Depends, Header, Request
from Entities.Api_Services import get_current_user
from Entities.Api_Services.social import clans
from Routers.social_router import extract_request_data

router = APIRouter(prefix="/clans", tags=["clans"])


@router.get("/directory")
async def search_clans_endpoint(
    q: str = "",
    join_type: str = "",
    language: str = "",
    only_joinable: bool = False,
    sort_by: str = "clan_score",
    skip: int = 0,
    limit: int = 30,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {
        "result": clans.search_clans_directory(
            viewer_id=str(user["_id"]),
            query_text=q,
            join_type=join_type,
            language=language,
            only_joinable=only_joinable,
            sort_by=sort_by,
            skip=skip,
            limit=limit,
        )
    }


@router.get("/my-clan")
async def get_my_clan_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": clans.get_clan_details(str(user["_id"]), "")}


@router.get("/invitations")
async def get_my_clan_invitations_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    uid = str(user["_id"])
    raw_invs = clans.game_database.clans_manager.get_user_clan_invitations(uid)
    out = []
    for inv in raw_invs:
        c_doc = clans.game_database.clans_manager.read_clan(str(inv.get("clan_id", "")))
        if c_doc:
            out.append(
                {
                    "invite_id": str(inv["_id"]),
                    "clan": clans._serialize_clan(c_doc),
                    "from_user_id": str(inv.get("from_user_id", "")),
                }
            )
    return {"result": out}


@router.get("/details/{clan_id}")
async def get_clan_details_endpoint(
    clan_id: str,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": clans.get_clan_details(str(user["_id"]), clan_id)}


@router.post("/create")
async def create_clan_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    return {
        "result": clans.create_clan(
            user_data=user,
            name=str(params.get("name", "")),
            tag=str(params.get("tag", "")),
            emblem_id=int(params.get("emblem_id", 1) or 1),
            description=str(params.get("description", "")),
            language=str(params.get("language", "fa")),
            join_type=str(params.get("join_type", "open")),
            min_score=int(params.get("min_score", 0) or 0),
            min_level=int(params.get("min_level", 1) or 1),
        )
    }


@router.post("/join")
async def join_clan_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    clan_id = str(params.get("clan_id", "")).strip()
    message = str(params.get("message", ""))
    return {"result": clans.join_or_request_clan(user, clan_id, message)}


@router.post("/join-request/respond")
async def respond_join_request_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    req_id = str(params.get("request_id", "")).strip()
    action = str(params.get("action", "accept")).strip()
    return {"result": clans.respond_clan_join_request(user, req_id, action)}


@router.post("/invite")
async def invite_to_clan_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    target_id = str(params.get("target_user_id", "")).strip()
    return {"result": clans.invite_player_to_clan(user, target_id)}


@router.post("/invite/respond")
async def respond_clan_invite_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    inv_id = str(params.get("invite_id", "")).strip()
    action = str(params.get("action", "accept")).strip()
    return {"result": clans.respond_clan_invitation(user, inv_id, action)}


@router.post("/leave")
async def leave_clan_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": clans.leave_clan(user)}


@router.post("/kick")
async def kick_member_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    target_id = str(params.get("target_user_id", "")).strip()
    return {"result": clans.kick_clan_member(user, target_id)}


@router.post("/role")
async def change_role_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    target_id = str(params.get("target_user_id", "")).strip()
    new_role = str(params.get("new_role", "member")).strip()
    return {"result": clans.change_member_role(user, target_id, new_role)}


@router.post("/transfer-leadership")
async def transfer_leadership_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    new_leader_id = str(params.get("new_leader_id", "")).strip()
    return {"result": clans.transfer_clan_leadership(user, new_leader_id)}


@router.post("/disband")
async def disband_clan_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": clans.disband_clan(user)}


@router.post("/settings")
async def update_clan_settings_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    return {"result": clans.update_clan_settings(user, params)}


@router.post("/challenge")
async def create_clan_challenge_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    return {
        "result": clans.create_clan_friendly_challenge(
            actor_data=user,
            game_type=str(params.get("game_type", "Ludo")),
            player_count=int(params.get("player_count", 2) or 2),
        )
    }
