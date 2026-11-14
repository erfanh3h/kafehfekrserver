import json
from fastapi import APIRouter, Depends, Header, Request
from Entities.Api_Services import get_current_user
from Entities.Api_Services.social import notifications
from Routers.social_router import extract_request_data

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
@router.get("/")
async def get_notifications_endpoint(
    skip: int = 0,
    limit: int = 40,
    unread_only: bool = False,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {
        "result": notifications.list_notifications(
            str(user["_id"]), skip=skip, limit=limit, unread_only=unread_only
        )
    }


@router.post("/read")
async def mark_notification_read_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    notif_id = str(params.get("notification_id", "")).strip()
    return {"result": notifications.mark_notification_read(str(user["_id"]), notif_id)}


@router.post("/read-all")
async def mark_all_notifications_read_endpoint(
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    return {"result": notifications.mark_all_notifications_read(str(user["_id"]))}


@router.post("/preferences")
async def update_notification_prefs_endpoint(
    request: Request,
    authorization: str = Header(...),
    user=Depends(get_current_user),
):
    params = await extract_request_data(request)
    prefs = params.get("preferences", params)
    if isinstance(prefs, str):
        try:
            prefs = json.loads(prefs)
        except Exception:
            prefs = {}
    return {"result": notifications.update_notification_preferences(str(user["_id"]), prefs if isinstance(prefs, dict) else {})}
