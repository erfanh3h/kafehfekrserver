from fastapi import APIRouter, Depends, Header, Request
from Entities.Api_Services import get_current_user
from Entities.Api_Services.social import messages
from Routers.social_router import extract_request_data

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/conversations")
async def list_conversations_endpoint(
    skip: int = 0,
    limit: int = 40,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": messages.get_conversations_list(str(user["_id"]), skip=skip, limit=limit)}


@router.get("/dm/{partner_id}")
async def get_dm_history_endpoint(
    partner_id: str,
    skip: int = 0,
    limit: int = 50,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": messages.get_direct_messages_history(str(user["_id"]), partner_id, skip=skip, limit=limit)}


@router.post("/dm/send")
async def send_dm_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    to_id = str(params.get("to_user_id", "")).strip()
    text = str(params.get("text", ""))
    return {"result": messages.send_direct_message(user, to_id, text)}


@router.post("/dm/read")
async def mark_dm_read_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    partner_id = str(params.get("partner_id", "")).strip()
    cleared = messages.game_database.direct_messages_manager.mark_conversation_read(str(user["_id"]), partner_id)
    return {"result": {"cleared": cleared}}


@router.get("/clan")
async def get_clan_chat_endpoint(
    clan_id: str = "",
    skip: int = 0,
    limit: int = 50,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": messages.get_clan_chat_history(str(user["_id"]), clan_id=clan_id, skip=skip, limit=limit)}


@router.post("/clan/send")
async def send_clan_chat_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    text = str(params.get("text", ""))
    return {"result": messages.send_clan_chat_message(user, text)}


@router.post("/clan/delete")
async def delete_clan_message_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    msg_id = str(params.get("message_id", "")).strip()
    return {"result": messages.delete_clan_chat_message(user, msg_id)}
