import json
from fastapi import APIRouter, Depends, Header, Request
from Entities.Api_Services import get_current_user
from Entities.Api_Services.social import (
    friends,
    profiles,
    invitations,
    leaderboards,
    moderation,
    notifications,
    clans,
)

router = APIRouter(prefix="/social", tags=["social"])


async def extract_request_data(request: Request) -> dict:
    data: dict = dict(request.query_params)
    content_type = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                data.update(body)
        elif "form" in content_type:
            form = await request.form()
            for k, v in form.items():
                data[k] = v
        else:
            raw = await request.body()
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                    if isinstance(parsed, dict):
                        data.update(parsed)
                except Exception:
                    form = await request.form()
                    for k, v in form.items():
                        data[k] = v
    except Exception:
        pass
    return data


@router.get("/overview")
async def social_overview(authorization: str = Header(...), user=Depends(get_current_user)):
    uid = str(user["_id"])
    f_list = friends.get_friends_list(uid)
    reqs = friends.get_friend_requests(uid)
    notifs = notifications.list_notifications(uid, limit=20)
    my_clan = clans.get_clan_details(uid, "")
    active_invites = invitations.list_active_invitations(uid)
    clan_invites = clans.game_database.clans_manager.get_user_clan_invitations(uid)
    return {
        "result": {
            "friends": f_list,
            "friend_requests": reqs,
            "clan_data": my_clan,
            "clan_invitations_count": len(clan_invites),
            "game_invitations": active_invites,
            "unread_notifications": notifs["unread_count"],
            "unread_dms": notifs["unread_dm_count"],
        }
    }


@router.get("/friends")
async def get_friends(authorization: str = Header(...), user=Depends(get_current_user)):
    uid = str(user["_id"])
    return {
        "result": {
            "friends": friends.get_friends_list(uid),
            "requests": friends.get_friend_requests(uid),
            "discover": friends.get_recently_played_and_suggestions(uid),
        }
    }


@router.get("/search-players")
async def search_players_endpoint(
    q: str = "",
    limit: int = 25,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": friends.search_players(str(user["_id"]), q, limit=limit)}


@router.post("/friend-request/send")
async def send_friend_request_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    target_id = str(params.get("to_user_id", params.get("target_user_id", ""))).strip()
    message = str(params.get("message", ""))
    return {"result": friends.send_friend_request(str(user["_id"]), target_id, message)}


@router.post("/friend-request/respond")
async def respond_friend_request_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    req_id = str(params.get("request_id", "")).strip()
    action = str(params.get("action", "accept")).strip()
    return {"result": friends.respond_friend_request(str(user["_id"]), req_id, action)}


@router.post("/friend/remove")
async def remove_friend_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    friend_id = str(params.get("friend_id", params.get("target_user_id", ""))).strip()
    return {"result": friends.remove_friend(str(user["_id"]), friend_id)}


@router.get("/profile/{target_user_id}")
async def get_public_profile_endpoint(
    target_user_id: str,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": profiles.get_public_profile(str(user["_id"]), target_user_id)}


@router.post("/profile/customize")
async def customize_profile_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    priv = params.get("privacy")
    if isinstance(priv, str):
        try:
            priv = json.loads(priv)
        except Exception:
            priv = None
    frame = int(params["profile_frame"]) if "profile_frame" in params and str(params["profile_frame"]).isdigit() else None
    return {
        "result": profiles.update_my_profile_customization(
            user_id=str(user["_id"]),
            profile_frame=frame,
            profile_title=params.get("profile_title"),
            profile_badge=params.get("profile_badge"),
            status_message=params.get("status_message"),
            privacy=priv if isinstance(priv, dict) else None,
        )
    }


@router.get("/leaderboards")
async def get_leaderboards_endpoint(
    board_type: str = "global_score",
    game_type: str = "",
    clan_id: str = "",
    limit: int = 30,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {
        "result": leaderboards.get_social_leaderboard(
            viewer_id=str(user["_id"]),
            board_type=board_type,
            game_type=game_type,
            clan_id=clan_id,
            limit=limit,
        )
    }


@router.get("/invitations")
async def list_game_invitations_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": invitations.list_active_invitations(str(user["_id"]))}


@router.post("/invitations/send")
async def send_game_invitation_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    return {
        "result": invitations.send_game_invitation(
            sender_data=user,
            to_user_id=str(params.get("to_user_id", "")),
            game_type=str(params.get("game_type", "Ludo")),
            invite_mode=str(params.get("invite_mode", "lobby")),
            lobby_id=str(params.get("lobby_id", "")),
            lobby_password=str(params.get("lobby_password", "")),
            player_count=int(params.get("player_count", 2) or 2),
        )
    }


@router.post("/invitations/respond")
async def respond_game_invitation_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    return {
        "result": invitations.respond_game_invitation(
            user_data=user,
            invite_id=str(params.get("invite_id", "")),
            action=str(params.get("action", "accept")),
        )
    }


@router.get("/blocks")
async def get_blocked_users_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": moderation.list_blocked_players(str(user["_id"]))}


@router.post("/block")
async def block_user_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    target_id = str(params.get("target_user_id", "")).strip()
    reason = str(params.get("reason", ""))
    return {"result": moderation.block_player(str(user["_id"]), target_id, reason)}


@router.post("/unblock")
async def unblock_user_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    target_id = str(params.get("target_user_id", "")).strip()
    return {"result": moderation.unblock_player(str(user["_id"]), target_id)}


@router.post("/report")
async def report_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    return {
        "result": moderation.report_target(
            reporter_id=str(user["_id"]),
            target_user_id=str(params.get("target_user_id", "")),
            reason=str(params.get("reason", "تخلف")),
            target_type=str(params.get("target_type", "player")),
            target_id=str(params.get("target_id", "")),
            details=str(params.get("details", "")),
        )
    }
