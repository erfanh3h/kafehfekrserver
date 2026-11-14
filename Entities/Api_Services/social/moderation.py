from Entities import Network_Exeptions
from Entities.Database import game_database
from Entities.Api_Services.social.security import (
    check_rate_limit,
    sanitize_text,
    sanitize_public_user_summary,
)


def block_player(user_id: str, target_user_id: str, reason: str = "") -> dict:
    uid, tid = str(user_id), str(target_user_id).strip()
    if not tid or uid == tid:
        raise Network_Exeptions.raise422(details="نمی‌توانید خودتان را مسدود کنید.")
    res = game_database.friends_manager.block_user(uid, tid, sanitize_text(reason, 160))
    return res


def unblock_player(user_id: str, target_user_id: str) -> dict:
    uid, tid = str(user_id), str(target_user_id).strip()
    ok = game_database.friends_manager.unblock_user(uid, tid)
    return {"unblocked": ok, "target_user_id": tid}


def list_blocked_players(user_id: str) -> list[dict]:
    b_ids = game_database.friends_manager.get_blocked_ids(user_id)
    if not b_ids:
        return []
    users = game_database.users_manager.read_users(b_ids)
    return [sanitize_public_user_summary(u) for u in users]


def report_target(
    reporter_id: str,
    target_user_id: str,
    reason: str,
    target_type: str = "player",
    target_id: str = "",
    details: str = "",
) -> dict:
    rid = str(reporter_id)
    tid = str(target_user_id).strip()
    check_rate_limit(rid, "report")
    if not tid or rid == tid:
        raise Network_Exeptions.raise422(details="گزارش نامعتبر است.")
    doc = game_database.reports_manager.create_report(
        reporter_id=rid,
        target_user_id=tid,
        reason=sanitize_text(reason or "تخلف", 80),
        target_type=target_type,
        target_id=target_id,
        details=sanitize_text(details, 350),
    )
    return {"report_id": str(doc["_id"]), "status": "submitted"}
