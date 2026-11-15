from datetime import datetime, timedelta
import os
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from bson import ObjectId

from Entities.Database import game_database
from Entities.Security import (
    hash_admin_password,
    verify_admin_password,
    create_admin_access_token,
)
from Commons.static_functions import create_random_name


def _clean_doc(doc: Any) -> Any:
    """Recursively converts MongoDB/BSON types into JSON serializable types."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [_clean_doc(item) for item in doc]
    if isinstance(doc, dict):
        cleaned = {}
        for k, v in doc.items():
            if isinstance(v, datetime):
                cleaned[k] = v.isoformat()
            elif isinstance(v, ObjectId):
                cleaned[k] = str(v)
            elif isinstance(v, (dict, list)):
                cleaned[k] = _clean_doc(v)
            else:
                cleaned[k] = v
        return cleaned
    return doc


# -------------------------------------------------------------
# Admin Auth & Management
# -------------------------------------------------------------

def login_admin(username: str, password: str) -> dict:
    clean_user = str(username or "").strip().lower()
    admin_doc = game_database.admin_manager.find_by_username(clean_user)
    if not admin_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    if not admin_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="این حساب کاربری غیرفعال شده است.",
        )

    if not verify_admin_password(password, admin_doc.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    game_database.admin_manager.update_last_login(admin_doc["_id"])
    token = create_admin_access_token(admin_doc)
    sanitized = game_database.admin_manager._sanitize_admin(admin_doc)
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": sanitized,
    }


def change_admin_password(admin_id: str, old_password: str, new_password: str) -> bool:
    admin_doc = game_database.admin_manager.find_by_id(admin_id)
    if not admin_doc:
        raise HTTPException(status_code=404, detail="حساب ادمین یافت نشد.")

    if not verify_admin_password(old_password, admin_doc.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="رمز عبور فعلی نادرست است.")

    if len(new_password or "") < 6:
        raise HTTPException(status_code=400, detail="رمز عبور جدید باید حداقل ۶ کاراکتر باشد.")

    hashed = hash_admin_password(new_password)
    game_database.admin_manager.update_admin(admin_id, password_hash=hashed)
    return True


def list_admins() -> list:
    return game_database.admin_manager.list_admins()


def create_admin(creator_id: str, data: dict) -> dict:
    username = data.get("username")
    password = data.get("password")
    full_name = data.get("full_name", "")
    role = data.get("role", "admin")
    permissions = data.get("permissions")

    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="رمز عبور باید حداقل ۶ کاراکتر باشد.")

    hashed = hash_admin_password(password)
    try:
        new_admin = game_database.admin_manager.create_admin(
            username=username,
            password_hash=hashed,
            full_name=full_name,
            role=role,
            permissions=permissions,
            created_by=creator_id,
        )
        return new_admin
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def update_admin(admin_id: str, data: dict) -> dict:
    password = data.get("password")
    pw_hash = hash_admin_password(password) if password else None

    updated = game_database.admin_manager.update_admin(
        admin_id=admin_id,
        full_name=data.get("full_name"),
        role=data.get("role"),
        permissions=data.get("permissions"),
        is_active=data.get("is_active"),
        password_hash=pw_hash,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="ادمین یافت نشد.")
    return updated


def delete_admin(admin_id: str, current_admin_id: str) -> bool:
    if str(admin_id) == str(current_admin_id):
        raise HTTPException(status_code=400, detail="نمی‌توانید حساب کاربری خودتان را حذف کنید.")
    success = game_database.admin_manager.delete_admin(admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="ادمین یافت نشد.")
    return True


# -------------------------------------------------------------
# Dashboard & Analytics
# -------------------------------------------------------------

def get_dashboard_stats() -> dict:
    users_col = game_database.users_manager.collection
    games_col = game_database.game_play_history_manager.collection
    purchases_col = game_database.purchase_manager.collection
    clans_col = game_database.clans_manager.clans
    reports_col = game_database.reports_manager.collection

    total_users = users_col.count_documents({})
    bot_users = users_col.count_documents({"_id": {"$regex": "^(bot_|test_bot)"}})
    real_users = max(0, total_users - bot_users)

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    users_today = users_col.count_documents({"join_date": {"$gte": today_start}})

    total_matches = games_col.count_documents({})
    live_matches = games_col.count_documents({"is_finished": False})
    finished_matches = games_col.count_documents({"is_finished": True})
    matches_today = games_col.count_documents({"start_date": {"$gte": today_start}})

    total_purchases = purchases_col.count_documents({})
    bazaar_purchases = purchases_col.count_documents({"market_type": {"$regex": "bazaar", "$options": "i"}})
    myket_purchases = purchases_col.count_documents({"market_type": {"$regex": "myket", "$options": "i"}})

    total_clans = clans_col.count_documents({})
    open_reports = reports_col.count_documents({"status": "open"})

    # Game type breakdown (last 200 matches)
    recent_games = list(games_col.find({}, {"game_types": 1}).sort([("start_date", -1)]).limit(200))
    game_type_counts = {}
    for g in recent_games:
        for gt in g.get("game_types", []):
            game_type_counts[gt] = game_type_counts.get(gt, 0) + 1

    config = game_database.config_manager.read_config() or {}

    return {
        "users": {
            "total": total_users,
            "real": real_users,
            "bots": bot_users,
            "joined_today": users_today,
        },
        "matches": {
            "total": total_matches,
            "live": live_matches,
            "finished": finished_matches,
            "today": matches_today,
            "breakdown": game_type_counts,
        },
        "purchases": {
            "total": total_purchases,
            "bazaar": bazaar_purchases,
            "myket": myket_purchases,
        },
        "clans_count": total_clans,
        "open_reports_count": open_reports,
        "config": {
            "is_queue_open": bool(config.get("is_queue_open", True)),
            "latest_version": config.get("latest_version", "2.0.0"),
            "allowed_version": config.get("allowed_version", "2.0.0"),
            "maintenance_mode": bool(config.get("maintenance_mode", False)),
            "announcement": config.get("announcement", ""),
        },
        "server_time": datetime.now().isoformat(),
    }


# -------------------------------------------------------------
# User Management
# -------------------------------------------------------------

def list_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    filter_type: Optional[str] = "all",  # all | real | bot | banned
    sort_by: str = "join_date",
    sort_order: int = -1,
) -> dict:
    col = game_database.users_manager.collection
    query = {}

    if filter_type == "bot":
        query["_id"] = {"$regex": "^(bot_|test_bot)"}
    elif filter_type == "real":
        query["_id"] = {"$not": {"$regex": "^(bot_|test_bot)"}}
    elif filter_type == "banned":
        query["is_active"] = False

    if search:
        s = str(search).strip()
        search_sub = {
            "$or": [
                {"_id": {"$regex": s, "$options": "i"}},
                {"username": {"$regex": s, "$options": "i"}},
                {"phone": {"$regex": s, "$options": "i"}},
            ]
        }
        if query:
            query = {"$and": [query, search_sub]}
        else:
            query = search_sub

    valid_sort_fields = ["join_date", "score", "coin", "xp", "last_time_played", "username"]
    field = sort_by if sort_by in valid_sort_fields else "join_date"
    direction = -1 if sort_order == -1 else 1

    total = col.count_documents(query)
    safe_limit = max(1, min(limit, 100))
    skip = max(0, (page - 1) * safe_limit)

    cursor = col.find(query).sort([(field, direction)]).skip(skip).limit(safe_limit)
    users = [_clean_doc(u) for u in cursor]

    return {
        "items": users,
        "total": total,
        "page": page,
        "limit": safe_limit,
        "total_pages": max(1, (total + safe_limit - 1) // safe_limit),
    }


def get_user_full_details(user_id: str) -> dict:
    uid = str(user_id)
    user = game_database.users_manager.read_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    history = game_database.user_history_manager.read_user_history(uid) or {}
    game_plays = game_database.game_play_history_manager.read_user_games_histories(uid, limit=15)
    purchases = list(game_database.purchase_manager.collection.find({"user_id": uid}).sort([("date", -1)]).limit(20))

    clan_info = None
    if user.get("created_clan_id"):
        clan_info = game_database.clans_manager.get_clan(user["created_clan_id"])
    else:
        mem = game_database.clans_manager.members.find_one({"user_id": uid})
        if mem and mem.get("clan_id"):
            clan_info = game_database.clans_manager.get_clan(mem["clan_id"])

    return {
        "user": _clean_doc(user),
        "history": _clean_doc(history),
        "recent_games": [_clean_doc(g) for g in game_plays],
        "purchases": [_clean_doc(p) for p in purchases],
        "clan": _clean_doc(clan_info),
    }


def update_user_profile(user_id: str, updates: dict) -> dict:
    uid = str(user_id)
    existing = game_database.users_manager.read_user(uid)
    if not existing:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    upd = {}
    if "username" in updates and updates["username"] is not None:
        upd["username"] = str(updates["username"]).strip()
    if "phone" in updates and updates["phone"] is not None:
        upd["phone"] = str(updates["phone"]).strip()
    if "coin" in updates and updates["coin"] is not None:
        upd["coin"] = max(0, int(updates["coin"]))
    if "score" in updates and updates["score"] is not None:
        upd["score"] = max(0, int(updates["score"]))
    if "xp" in updates and updates["xp"] is not None:
        upd["xp"] = max(0, int(updates["xp"]))
    if "is_active" in updates and updates["is_active"] is not None:
        upd["is_active"] = bool(updates["is_active"])
    if "image" in updates and updates["image"] is not None:
        upd["image"] = int(updates["image"])

    if upd:
        game_database.users_manager.collection.find_one_and_update(
            {"_id": uid}, {"$set": upd}
        )

    return _clean_doc(game_database.users_manager.read_user(uid))


def adjust_user_currency(user_id: str, field: str, amount: int, reason: str = "", admin_id: str = "") -> dict:
    uid = str(user_id)
    user = game_database.users_manager.read_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    valid_fields = ["coin", "score", "xp"]
    if field not in valid_fields:
        raise HTTPException(status_code=400, detail="فیلد نامعتبر است.")

    current = int(user.get(field, 0))
    new_val = max(0, current + amount)
    game_database.users_manager.collection.find_one_and_update(
        {"_id": uid},
        {"$set": {field: new_val}}
    )

    # Log action
    _log_admin_action(admin_id, "adjust_currency", {
        "user_id": uid,
        "field": field,
        "amount": amount,
        "previous": current,
        "new": new_val,
        "reason": reason,
    })

    return {
        "user_id": uid,
        "field": field,
        "previous_value": current,
        "new_value": new_val,
        "adjustment": amount,
    }


def toggle_user_ban(user_id: str, is_active: bool, reason: str = "", admin_id: str = "") -> dict:
    uid = str(user_id)
    user = game_database.users_manager.read_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    game_database.users_manager.collection.find_one_and_update(
        {"_id": uid},
        {"$set": {"is_active": bool(is_active)}}
    )

    _log_admin_action(admin_id, "toggle_user_status", {
        "user_id": uid,
        "is_active": is_active,
        "reason": reason,
    })

    return {"user_id": uid, "is_active": is_active}


def reset_user_locks(user_id: str) -> dict:
    uid = str(user_id)
    game_database.users_manager.collection.find_one_and_update(
        {"_id": uid},
        {"$set": {"open_game_id": "", "open_pre_game_id": ""}}
    )
    return {"user_id": uid, "status": "locks_cleared"}


def delete_user_account(user_id: str, admin_id: str = "") -> bool:
    uid = str(user_id)
    game_database.users_manager.delete_user(uid)
    _log_admin_action(admin_id, "delete_user", {"user_id": uid})
    return True


def bulk_adjust_coins(amount: int, filter_type: str = "all", reason: str = "", admin_id: str = "") -> dict:
    col = game_database.users_manager.collection
    query = {}
    if filter_type == "real":
        query["_id"] = {"$not": {"$regex": "^(bot_|test_bot)"}}
    elif filter_type == "active":
        query["is_active"] = True

    res = col.update_many(query, {"$inc": {"coin": amount}})
    _log_admin_action(admin_id, "bulk_adjust_coins", {
        "amount": amount,
        "filter": filter_type,
        "matched_count": res.matched_count,
        "modified_count": res.modified_count,
        "reason": reason,
    })
    return {
        "modified_count": res.modified_count,
        "amount": amount,
    }


# -------------------------------------------------------------
# Games & Matches Management
# -------------------------------------------------------------

def list_live_games() -> list:
    col = game_database.game_play_history_manager.collection
    cursor = col.find({"is_finished": False}).sort([("start_date", -1)]).limit(100)
    return [_clean_doc(g) for g in cursor]


def list_game_history(
    page: int = 1,
    limit: int = 20,
    game_type: Optional[str] = None,
    game_score_type: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    col = game_database.game_play_history_manager.collection
    query = {"is_finished": True}

    if game_type:
        query["game_types"] = game_type
    if game_score_type:
        query["game_score_type"] = game_score_type
    if user_id:
        uid = str(user_id)
        query["$or"] = [
            {"user_ids": uid},
            {"user1_id": uid},
            {"user2_id": uid},
        ]

    total = col.count_documents(query)
    safe_limit = max(1, min(limit, 100))
    skip = max(0, (page - 1) * safe_limit)

    cursor = col.find(query).sort([("start_date", -1)]).skip(skip).limit(safe_limit)
    games = [_clean_doc(g) for g in cursor]

    return {
        "items": games,
        "total": total,
        "page": page,
        "limit": safe_limit,
        "total_pages": max(1, (total + safe_limit - 1) // safe_limit),
    }


def get_game_play_details(game_play_id: str) -> dict:
    gid = str(game_play_id)
    match = game_database.game_play_history_manager.read_game_play_history(gid)
    if not match:
        raise HTTPException(status_code=404, detail="بازی یافت نشد.")

    rounds = game_database.game_history_manager.read_rounds_by_game_play_id(gid)
    return {
        "match": _clean_doc(match),
        "rounds": [_clean_doc(r) for r in rounds],
    }


def terminate_game_session(game_play_id: str, admin_id: str = "") -> dict:
    gid = str(game_play_id)
    match = game_database.game_play_history_manager.read_game_play_history(gid)
    if not match:
        raise HTTPException(status_code=404, detail="شناسه بازی نامعتبر است.")

    # Mark game finished
    game_database.game_play_history_manager.collection.find_one_and_update(
        {"_id": gid},
        {"$set": {"is_finished": True, "finish_date": datetime.now(), "terminated_by_admin": True}}
    )

    # Release user locks
    user_ids = match.get("user_ids", [])
    if not user_ids:
        for i in range(1, 5):
            k = f"user{i}_id"
            if match.get(k):
                user_ids.append(match[k])

    if user_ids:
        game_database.users_manager.collection.update_many(
            {"_id": {"$in": user_ids}, "open_game_id": gid},
            {"$set": {"open_game_id": ""}}
        )

    _log_admin_action(admin_id, "terminate_game", {"game_id": gid, "released_users": user_ids})
    return {"game_id": gid, "status": "terminated", "released_users": user_ids}


def cleanup_stuck_games(max_age_minutes: int = 120, admin_id: str = "") -> dict:
    col = game_database.game_play_history_manager.collection
    cutoff = datetime.now() - timedelta(minutes=max_age_minutes)

    # Find games older than cutoff that are not finished
    stuck_games = list(col.find({"is_finished": False, "start_date": {"$lt": cutoff}}))
    count = len(stuck_games)

    for g in stuck_games:
        gid = str(g["_id"])
        col.find_one_and_update(
            {"_id": gid},
            {"$set": {"is_finished": True, "finish_date": datetime.now(), "auto_cleaned": True}}
        )
        uids = g.get("user_ids", [])
        if uids:
            game_database.users_manager.collection.update_many(
                {"_id": {"$in": uids}, "open_game_id": gid},
                {"$set": {"open_game_id": ""}}
            )

    _log_admin_action(admin_id, "cleanup_stuck_games", {"cleaned_count": count, "cutoff_minutes": max_age_minutes})
    return {"cleaned_games_count": count}


# -------------------------------------------------------------
# System Config & Queue Control
# -------------------------------------------------------------

def get_system_config() -> dict:
    cfg = game_database.config_manager.read_config() or {}
    return _clean_doc(cfg)


def set_queue_status(is_open: bool, hour: int = 0, minute: int = 0, admin_id: str = "") -> dict:
    game_database.config_manager.update_config(is_queue_open=bool(is_open))
    _log_admin_action(admin_id, "set_queue_status", {"is_open": is_open, "hour": hour, "minute": minute})
    return {"is_queue_open": is_open, "hour": hour, "minute": minute}


def set_app_versions(allowed_version: str, latest_version: str, admin_id: str = "") -> dict:
    game_database.config_manager.update_config(
        allowed_version=str(allowed_version).strip(),
        latest_version=str(latest_version).strip(),
    )
    _log_admin_action(admin_id, "set_app_versions", {"allowed": allowed_version, "latest": latest_version})
    return {"allowed_version": allowed_version, "latest_version": latest_version}


def set_announcement_banner(announcement: str, is_active: bool = True, admin_id: str = "") -> dict:
    game_database.config_manager.collection.find_one_and_update(
        {},
        {"$set": {"announcement": str(announcement or "").strip(), "announcement_active": bool(is_active)}}
    )
    _log_admin_action(admin_id, "set_announcement", {"announcement": announcement, "is_active": is_active})
    return {"announcement": announcement, "is_active": is_active}


# -------------------------------------------------------------
# Purchases & Store Management
# -------------------------------------------------------------

def list_purchases(
    page: int = 1,
    limit: int = 20,
    market_type: Optional[str] = None,
    product_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    col = game_database.purchase_manager.collection
    query = {}

    if market_type:
        query["market_type"] = {"$regex": market_type, "$options": "i"}
    if product_id:
        query["product_id"] = str(product_id)
    if user_id:
        query["user_id"] = str(user_id)

    total = col.count_documents(query)
    safe_limit = max(1, min(limit, 100))
    skip = max(0, (page - 1) * safe_limit)

    cursor = col.find(query).sort([("date", -1)]).skip(skip).limit(safe_limit)
    items = [_clean_doc(p) for p in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": safe_limit,
        "total_pages": max(1, (total + safe_limit - 1) // safe_limit),
    }


# -------------------------------------------------------------
# Clans Management
# -------------------------------------------------------------

def list_clans(page: int = 1, limit: int = 20, search: Optional[str] = None) -> dict:
    col = game_database.clans_manager.clans
    query = {}
    if search:
        s = str(search).strip()
        query["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"tag": {"$regex": s, "$options": "i"}},
            {"_id": {"$regex": s, "$options": "i"}},
        ]

    total = col.count_documents(query)
    safe_limit = max(1, min(limit, 100))
    skip = max(0, (page - 1) * safe_limit)

    cursor = col.find(query).sort([("trophies", -1), ("level", -1)]).skip(skip).limit(safe_limit)
    items = [_clean_doc(c) for c in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": safe_limit,
        "total_pages": max(1, (total + safe_limit - 1) // safe_limit),
    }


def get_clan_full_details(clan_id: str) -> dict:
    cid = str(clan_id)
    clan = game_database.clans_manager.get_clan(cid)
    if not clan:
        raise HTTPException(status_code=404, detail="کلن یافت نشد.")

    members = list(game_database.clans_manager.members.find({"clan_id": cid}))
    challenges = list(game_database.clans_manager.challenges.find({"clan_id": cid}).sort([("created_at", -1)]).limit(20))

    return {
        "clan": _clean_doc(clan),
        "members": [_clean_doc(m) for m in members],
        "challenges": [_clean_doc(c) for c in challenges],
    }


def update_clan_info(clan_id: str, updates: dict, admin_id: str = "") -> dict:
    cid = str(clan_id)
    clan = game_database.clans_manager.get_clan(cid)
    if not clan:
        raise HTTPException(status_code=404, detail="کلن یافت نشد.")

    upd = {}
    if "name" in updates and updates["name"]:
        upd["name"] = str(updates["name"]).strip()
    if "tag" in updates and updates["tag"]:
        upd["tag"] = str(updates["tag"]).strip()
    if "description" in updates:
        upd["description"] = str(updates["description"]).strip()
    if "level" in updates and updates["level"] is not None:
        upd["level"] = max(1, int(updates["level"]))
    if "trophies" in updates and updates["trophies"] is not None:
        upd["trophies"] = max(0, int(updates["trophies"]))

    if upd:
        game_database.clans_manager.clans.find_one_and_update({"_id": cid}, {"$set": upd})

    _log_admin_action(admin_id, "update_clan", {"clan_id": cid, "updates": upd})
    return _clean_doc(game_database.clans_manager.get_clan(cid))


def disband_clan(clan_id: str, admin_id: str = "") -> bool:
    cid = str(clan_id)
    clan = game_database.clans_manager.get_clan(cid)
    if not clan:
        raise HTTPException(status_code=404, detail="کلن یافت نشد.")

    # Remove all members and references
    game_database.clans_manager.members.delete_many({"clan_id": cid})
    game_database.clans_manager.clans.delete_one({"_id": cid})
    game_database.users_manager.collection.update_many(
        {"created_clan_id": cid},
        {"$set": {"created_clan_id": None}}
    )

    _log_admin_action(admin_id, "disband_clan", {"clan_id": cid, "clan_name": clan.get("name")})
    return True


# -------------------------------------------------------------
# Reports & Moderation
# -------------------------------------------------------------

def list_reports(page: int = 1, limit: int = 20, status_filter: Optional[str] = None) -> dict:
    col = game_database.reports_manager.collection
    query = {}
    if status_filter and status_filter != "all":
        query["status"] = status_filter

    total = col.count_documents(query)
    safe_limit = max(1, min(limit, 100))
    skip = max(0, (page - 1) * safe_limit)

    cursor = col.find(query).sort([("created_at", -1)]).skip(skip).limit(safe_limit)
    items = [_clean_doc(r) for r in cursor]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": safe_limit,
        "total_pages": max(1, (total + safe_limit - 1) // safe_limit),
    }


def update_report_status(report_id: str, new_status: str, admin_notes: str = "", admin_id: str = "") -> dict:
    col = game_database.reports_manager.collection
    rid = str(report_id)
    rep = col.find_one({"_id": rid})
    if not rep:
        raise HTTPException(status_code=404, detail="گزارش یافت نشد.")

    upd = {
        "status": new_status,
        "admin_notes": str(admin_notes or ""),
        "resolved_at": datetime.now(),
        "resolved_by": admin_id,
    }
    col.find_one_and_update({"_id": rid}, {"$set": upd})
    _log_admin_action(admin_id, "update_report", {"report_id": rid, "status": new_status, "notes": admin_notes})
    return _clean_doc(col.find_one({"_id": rid}))


# -------------------------------------------------------------
# System Backups & Audit Logs
# -------------------------------------------------------------

def trigger_manual_backup(admin_id: str = "") -> dict:
    from Entities.Database.backup import start_backup
    try:
        start_backup()
        _log_admin_action(admin_id, "manual_backup", {"timestamp": datetime.now().isoformat()})
        return {"status": "success", "message": "پشتیبان‌گیری از پایگاه داده با موفقیت انجام شد."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پشتیبان‌گیری: {str(e)}")


def list_system_backups() -> list:
    backup_dir = os.getenv("BACKUP_DIR", "Backups/")
    if not os.path.exists(backup_dir):
        return []

    files = []
    for f in os.listdir(backup_dir):
        full_path = os.path.join(backup_dir, f)
        if os.path.isfile(full_path):
            stat = os.stat(full_path)
            files.append({
                "filename": f,
                "size_bytes": stat.st_size,
                "size_formatted": f"{stat.st_size / (1024*1024):.2f} MB" if stat.st_size > 1024*1024 else f"{stat.st_size / 1024:.2f} KB",
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return sorted(files, key=lambda x: x["modified"], reverse=True)


def list_audit_logs(limit: int = 50) -> list:
    audit_col = game_database.base_db["admin_audit_logs"]
    cursor = audit_col.find({}).sort([("timestamp", -1)]).limit(limit)
    return [_clean_doc(doc) for doc in cursor]


def _log_admin_action(admin_id: str, action: str, details: dict):
    try:
        audit_col = game_database.base_db["admin_audit_logs"]
        audit_col.insert_one({
            "_id": f"log_{create_random_name()}",
            "admin_id": str(admin_id or "system"),
            "action": action,
            "details": details,
            "timestamp": datetime.now(),
        })
    except Exception as e:
        print(f"[AdminAudit] Error saving audit log: {e}")
