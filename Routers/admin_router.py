from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Body, HTTPException, status
from pydantic import BaseModel, Field

from Entities.Security import get_current_admin
from Entities.Api_Services import admin_service


router = APIRouter(prefix='/admin', tags=['admin'])


# -------------------------------------------------------------
# Pydantic Request Models
# -------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, description="نام کاربری ادمین")
    password: str = Field(..., min_length=4, description="رمز عبور")


class AdminChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=4)
    new_password: str = Field(..., min_length=6)


class CreateAdminRequest(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = ""
    role: Optional[str] = "admin"
    permissions: Optional[List[str]] = None


class UpdateAdminRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None
    coin: Optional[int] = None
    score: Optional[int] = None
    xp: Optional[int] = None
    is_active: Optional[bool] = None
    image: Optional[int] = None


class AdjustCurrencyRequest(BaseModel):
    field: str = Field(..., description="coin | score | xp")
    amount: int = Field(..., description="مقدار افزایش یا کاهش (مثبت یا منفی)")
    reason: Optional[str] = ""


class ToggleBanRequest(BaseModel):
    is_active: bool = Field(..., description="وضعیت فعال بودن (True: فعال، False: بن شده)")
    reason: Optional[str] = ""


class BulkCoinsRequest(BaseModel):
    amount: int = Field(..., description="تعداد سکه اهدایی به هر کاربر")
    filter_type: Optional[str] = "all"  # all | real | active
    reason: Optional[str] = "هدیه مدیریت"


class QueueConfigRequest(BaseModel):
    is_open: bool
    hour: Optional[int] = 0
    minute: Optional[int] = 0


class VersionConfigRequest(BaseModel):
    allowed_version: str
    latest_version: str


class AnnouncementRequest(BaseModel):
    announcement: str
    is_active: Optional[bool] = True


class UpdateClanRequest(BaseModel):
    name: Optional[str] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None
    trophies: Optional[int] = None


class UpdateReportRequest(BaseModel):
    status: str = Field(..., description="resolved | dismissed | open")
    admin_notes: Optional[str] = ""


# -------------------------------------------------------------
# Admin Authentication & Self Profile
# -------------------------------------------------------------

@router.post("/auth/login")
async def admin_login(payload: AdminLoginRequest):
    return admin_service.login_admin(payload.username, payload.password)


@router.get("/auth/me")
async def admin_get_me(current_admin: dict = Depends(get_current_admin)):
    return {"admin": current_admin}


@router.post("/auth/change-password")
async def admin_change_password(
    payload: AdminChangePasswordRequest,
    current_admin: dict = Depends(get_current_admin),
):
    success = admin_service.change_admin_password(
        current_admin["_id"], payload.old_password, payload.new_password
    )
    return {"status": "success", "message": "رمز عبور با موفقیت تغییر کرد."}


# -------------------------------------------------------------
# Admin Staff Management (Role-Based Access)
# -------------------------------------------------------------

@router.get("/admins")
async def get_all_admins(current_admin: dict = Depends(get_current_admin)):
    if current_admin.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="فقط مدیر ارشد دسترسی دارد.")
    return {"admins": admin_service.list_admins()}


@router.post("/admins")
async def create_new_admin(
    payload: CreateAdminRequest,
    current_admin: dict = Depends(get_current_admin),
):
    if current_admin.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="فقط مدیر ارشد دسترسی دارد.")
    new_adm = admin_service.create_admin(current_admin["_id"], payload.model_dump())
    return {"admin": new_adm}


@router.put("/admins/{admin_id}")
async def update_admin_user(
    admin_id: str,
    payload: UpdateAdminRequest,
    current_admin: dict = Depends(get_current_admin),
):
    if current_admin.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="فقط مدیر ارشد دسترسی دارد.")
    updated = admin_service.update_admin(admin_id, payload.model_dump(exclude_unset=True))
    return {"admin": updated}


@router.delete("/admins/{admin_id}")
async def delete_admin_user(
    admin_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    if current_admin.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="فقط مدیر ارشد دسترسی دارد.")
    success = admin_service.delete_admin(admin_id, current_admin["_id"])
    return {"status": "success", "deleted": success}


# -------------------------------------------------------------
# Dashboard & Analytics
# -------------------------------------------------------------

@router.get("/stats")
async def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    return admin_service.get_dashboard_stats()


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    current_admin: dict = Depends(get_current_admin),
):
    return {"logs": admin_service.list_audit_logs(limit=limit)}


# -------------------------------------------------------------
# User Management
# -------------------------------------------------------------

@router.get("/users")
async def get_users_list(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    filter_type: Optional[str] = "all",
    sort_by: str = "join_date",
    sort_order: int = -1,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.list_users(
        page=page,
        limit=limit,
        search=search,
        filter_type=filter_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.get_user_full_details(user_id)


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    current_admin: dict = Depends(get_current_admin),
):
    updated = admin_service.update_user_profile(user_id, payload.model_dump(exclude_unset=True))
    return {"user": updated}


@router.post("/users/{user_id}/adjust-currency")
async def adjust_user_currency(
    user_id: str,
    payload: AdjustCurrencyRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.adjust_user_currency(
        user_id=user_id,
        field=payload.field,
        amount=payload.amount,
        reason=payload.reason,
        admin_id=current_admin["_id"],
    )


@router.post("/users/{user_id}/toggle-ban")
async def toggle_user_ban(
    user_id: str,
    payload: ToggleBanRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.toggle_user_ban(
        user_id=user_id,
        is_active=payload.is_active,
        reason=payload.reason,
        admin_id=current_admin["_id"],
    )


@router.post("/users/{user_id}/reset-locks")
async def reset_user_locks(
    user_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.reset_user_locks(user_id)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    deleted = admin_service.delete_user_account(user_id, admin_id=current_admin["_id"])
    return {"status": "success", "deleted": deleted}


@router.post("/users/bulk-coins")
async def bulk_distribute_coins(
    payload: BulkCoinsRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.bulk_adjust_coins(
        amount=payload.amount,
        filter_type=payload.filter_type,
        reason=payload.reason,
        admin_id=current_admin["_id"],
    )


# -------------------------------------------------------------
# Games & Matches Management
# -------------------------------------------------------------

@router.get("/games/live")
async def get_live_games(current_admin: dict = Depends(get_current_admin)):
    return {"games": admin_service.list_live_games()}


@router.get("/games/history")
async def get_game_history(
    page: int = 1,
    limit: int = 20,
    game_type: Optional[str] = None,
    game_score_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.list_game_history(
        page=page,
        limit=limit,
        game_type=game_type,
        game_score_type=game_score_type,
        user_id=user_id,
    )


@router.get("/games/{game_id}")
async def get_game_details(
    game_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.get_game_play_details(game_id)


@router.post("/games/{game_id}/terminate")
async def terminate_game(
    game_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.terminate_game_session(game_id, admin_id=current_admin["_id"])


@router.post("/games/cleanup-stuck")
async def cleanup_stuck_games(
    max_age_minutes: int = 120,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.cleanup_stuck_games(
        max_age_minutes=max_age_minutes,
        admin_id=current_admin["_id"],
    )


# -------------------------------------------------------------
# System Config & Queue Control
# -------------------------------------------------------------

@router.get("/config")
async def get_config(current_admin: dict = Depends(get_current_admin)):
    return admin_service.get_system_config()


@router.post("/config/queue")
async def set_queue(
    payload: QueueConfigRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.set_queue_status(
        is_open=payload.is_open,
        hour=payload.hour,
        minute=payload.minute,
        admin_id=current_admin["_id"],
    )


@router.post("/config/version")
async def set_version(
    payload: VersionConfigRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.set_app_versions(
        allowed_version=payload.allowed_version,
        latest_version=payload.latest_version,
        admin_id=current_admin["_id"],
    )


@router.post("/config/announcement")
async def set_announcement(
    payload: AnnouncementRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.set_announcement_banner(
        announcement=payload.announcement,
        is_active=payload.is_active,
        admin_id=current_admin["_id"],
    )


# -------------------------------------------------------------
# Purchases & Store Management
# -------------------------------------------------------------

@router.get("/purchases")
async def get_purchases(
    page: int = 1,
    limit: int = 20,
    market_type: Optional[str] = None,
    product_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.list_purchases(
        page=page,
        limit=limit,
        market_type=market_type,
        product_id=product_id,
        user_id=user_id,
    )


# -------------------------------------------------------------
# Clans Management
# -------------------------------------------------------------

@router.get("/clans")
async def get_clans(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.list_clans(page=page, limit=limit, search=search)


@router.get("/clans/{clan_id}")
async def get_clan(
    clan_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.get_clan_full_details(clan_id)


@router.put("/clans/{clan_id}")
async def update_clan(
    clan_id: str,
    payload: UpdateClanRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.update_clan_info(
        clan_id=clan_id,
        updates=payload.model_dump(exclude_unset=True),
        admin_id=current_admin["_id"],
    )


@router.delete("/clans/{clan_id}")
async def disband_clan(
    clan_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    success = admin_service.disband_clan(clan_id, admin_id=current_admin["_id"])
    return {"status": "success", "disbanded": success}


# -------------------------------------------------------------
# Reports & Moderation
# -------------------------------------------------------------

@router.get("/reports")
async def get_reports(
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.list_reports(page=page, limit=limit, status_filter=status_filter)


@router.put("/reports/{report_id}")
async def update_report(
    report_id: str,
    payload: UpdateReportRequest,
    current_admin: dict = Depends(get_current_admin),
):
    return admin_service.update_report_status(
        report_id=report_id,
        new_status=payload.status,
        admin_notes=payload.admin_notes,
        admin_id=current_admin["_id"],
    )


# -------------------------------------------------------------
# System Operations & Backups
# -------------------------------------------------------------

@router.post("/system/backup")
async def trigger_backup(current_admin: dict = Depends(get_current_admin)):
    return admin_service.trigger_manual_backup(admin_id=current_admin["_id"])


@router.get("/system/backups")
async def list_backups(current_admin: dict = Depends(get_current_admin)):
    return {"backups": admin_service.list_system_backups()}


# -------------------------------------------------------------
# Backward-Compatible Legacy Endpoints
# -------------------------------------------------------------

@router.get("/unfinished-games")
async def legacy_unfinished_games(token: str):
    from Entities.Api_Services import game
    return {"result": game.get_unfinished_games(token)}


@router.get("/finished-games")
async def legacy_finished_games(token: str):
    from Entities.Api_Services import game
    return {"result": game.get_finished_games(token)}


@router.get("/delete-unfinished-games")
async def legacy_delete_unfinished_games(token: str):
    from Entities.Api_Services import game
    return {"result": game.delete_unfinished_games(token)}


@router.get("/config-let-queue")
async def legacy_config_let_queue(token: str, value: bool, hour: int = 0, minute: int = 0):
    from Entities.Api_Services import set_config_let_queue
    set_config_let_queue(token, value, hour, minute)
    return {"result": value}


@router.get("/change-version")
async def legacy_change_version(token: str, allowed: str, latest: str):
    from Entities.Api_Services import change_version
    change_version(token, allowed, latest)
    return {"result": [allowed, latest]}


@router.get("/users-count")
async def legacy_users_count(token: str):
    from Entities.Api_Services import user
    return {"result": user.get_users_count(token)}


@router.get("/update-coin")
async def legacy_update_coin(token: str, user_id: str, value: int):
    from Entities.Api_Services import user
    user.update_coin_by_admin(token, user_id, value)
    return {"result": value}
