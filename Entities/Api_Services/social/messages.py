import re
from Entities import Network_Exeptions
from Entities.Database import game_database
from Entities.Database.social.clans_collection import CLAN_ROLE_RANK
from Entities.Api_Services.social.security import (
    check_rate_limit,
    sanitize_text,
    serialize_dt,
    sanitize_public_user_summary,
)


def _format_dm(msg: dict) -> dict:
    return {
        "message_id": str(msg["_id"]),
        "conversation_id": str(msg.get("conversation_id", "")),
        "from_user_id": str(msg.get("from_user_id", "")),
        "to_user_id": str(msg.get("to_user_id", "")),
        "text": str(msg.get("text", "")),
        "is_read": bool(msg.get("is_read", False)),
        "read_at": serialize_dt(msg.get("read_at")),
        "created_at": serialize_dt(msg.get("created_at")),
    }


def _format_clan_msg(msg: dict) -> dict:
    return {
        "message_id": str(msg["_id"]),
        "clan_id": str(msg.get("clan_id", "")),
        "sender_id": str(msg.get("sender_id", "")),
        "sender_name": str(msg.get("sender_name", "")),
        "sender_image": int(msg.get("sender_image", 0) or 0),
        "sender_role": str(msg.get("sender_role", "member")),
        "text": str(msg.get("text", "")),
        "msg_type": str(msg.get("msg_type", "text")),
        "mentions": list(msg.get("mentions", []) or []),
        "metadata": msg.get("metadata", {}) or {},
        "created_at": serialize_dt(msg.get("created_at")),
    }


def send_direct_message(sender_data: dict, to_user_id: str, text: str) -> dict:
    fid = str(sender_data["_id"])
    tid = str(to_user_id).strip()
    check_rate_limit(fid, "dm_send")
    if not tid or fid == tid:
        raise Network_Exeptions.raise422(details="گیرنده پیام نامعتبر است.")

    clean_text = sanitize_text(text, 500)
    if not clean_text:
        raise Network_Exeptions.raise422(details="متن پیام نمی‌تواند خالی باشد.")

    if game_database.friends_manager.is_blocked(fid, tid):
        raise Network_Exeptions.raise403(details="امکان ارسال پیام به این بازیکن وجود ندارد.")

    target_user = game_database.users_manager.read_user(tid)
    if not target_user:
        raise Network_Exeptions.raise404(details="بازیکن مورد نظر یافت نشد.")

    priv = target_user.get("privacy") if isinstance(target_user.get("privacy"), dict) else {}
    dm_policy = str(priv.get("allow_dms", "everyone"))
    if dm_policy == "none":
        raise Network_Exeptions.raise403(details="این بازیکن دریافت پیام خصوصی را بسته است.")
    if dm_policy == "friends" and not game_database.friends_manager.are_friends(fid, tid):
        raise Network_Exeptions.raise403(details="این بازیکن فقط از دوستان خود پیام دریافت می‌کند.")

    msg_doc = game_database.direct_messages_manager.create_direct_message(fid, tid, clean_text)
    game_database.notifications_manager.create_notification(
        user_id=tid,
        notif_type="direct_message_received",
        title=f"💬 پیام جدید از {sender_data.get('username', 'بازیکن')}",
        body=clean_text[:100],
        actor_id=fid,
        actor_name=str(sender_data.get("username", "بازیکن")),
        actor_image=int(sender_data.get("image", 0) or 0),
        payload={"conversation_id": msg_doc["conversation_id"], "from_user_id": fid},
        category="direct_messages",
    )
    return _format_dm(msg_doc)


def get_conversations_list(user_id: str, skip: int = 0, limit: int = 40) -> list[dict]:
    uid = str(user_id)
    blocked = game_database.friends_manager.get_all_block_related_ids(uid)
    convs = game_database.direct_messages_manager.get_user_conversations(uid, skip=skip, limit=limit)
    partner_ids = []
    for c in convs:
        for p in c.get("participants", []):
            if str(p) != uid:
                partner_ids.append(str(p))

    users_map = {str(u["_id"]): u for u in game_database.users_manager.read_users(partner_ids)}
    pres_map = game_database.presence_manager.get_bulk_presence(partner_ids)

    out = []
    for c in convs:
        parts = [str(p) for p in c.get("participants", []) if str(p) != uid]
        pid = parts[0] if parts else ""
        if not pid or pid in blocked:
            continue
        u_doc = users_map.get(pid, {"_id": pid, "username": "بازیکن", "image": 0, "score": 0, "xp": 0})
        u_sum = sanitize_public_user_summary(u_doc, pres_map.get(pid))
        unread_map = c.get("unread_counts", {}) or {}
        out.append(
            {
                "conversation_id": str(c["_id"]),
                "partner": u_sum,
                "last_message": str(c.get("last_message", "")),
                "last_sender_id": str(c.get("last_sender_id", "")),
                "unread_count": int(unread_map.get(uid, 0) or 0),
                "updated_at": serialize_dt(c.get("updated_at")),
            }
        )
    return out


def get_direct_messages_history(user_id: str, partner_id: str, skip: int = 0, limit: int = 50) -> dict:
    uid, pid = str(user_id), str(partner_id).strip()
    if game_database.friends_manager.is_blocked(uid, pid):
        raise Network_Exeptions.raise403(details="امکان دسترسی به این گفت‌وگو وجود ندارد.")
    game_database.direct_messages_manager.mark_conversation_read(uid, pid)
    msgs = game_database.direct_messages_manager.get_conversation_messages(uid, pid, skip=skip, limit=limit)
    partner_doc = game_database.users_manager.read_user(pid)
    pres = game_database.presence_manager.get_presence(pid)
    return {
        "partner": sanitize_public_user_summary(partner_doc, pres) if partner_doc else {"user_id": pid},
        "messages": [_format_dm(m) for m in msgs],
    }


def send_clan_chat_message(sender_data: dict, text: str) -> dict:
    uid = str(sender_data["_id"])
    check_rate_limit(uid, "clan_chat")
    mem = game_database.clans_manager.get_user_membership(uid)
    if not mem:
        raise Network_Exeptions.raise403(details="شما عضو هیچ کلنی نیستید.")
    cid = str(mem["clan_id"])
    clean_text = sanitize_text(text, 500)
    if not clean_text:
        raise Network_Exeptions.raise422(details="متن پیام نمی‌تواند خالی باشد.")

    mentions = re.findall(r"@([A-Za-z0-9_\u0600-\u06FF]+)", clean_text)
    msg_doc = game_database.clan_messages_manager.create_message(
        clan_id=cid,
        sender_id=uid,
        sender_name=str(sender_data.get("username", "بازیکن")),
        sender_image=int(sender_data.get("image", 0) or 0),
        sender_role=str(mem.get("role", "member")),
        text=clean_text,
        msg_type="text",
        mentions=mentions[:5],
    )
    return _format_clan_msg(msg_doc)


def get_clan_chat_history(user_id: str, clan_id: str = "", skip: int = 0, limit: int = 50) -> list[dict]:
    uid = str(user_id)
    mem = game_database.clans_manager.get_user_membership(uid)
    if not mem:
        raise Network_Exeptions.raise403(details="شما عضو کلن نیستید.")
    cid = str(clan_id or mem["clan_id"])
    if str(mem["clan_id"]) != cid:
        raise Network_Exeptions.raise403(details="دسترسی به چت خصوصی کلن دیگران مجاز نیست.")
    msgs = game_database.clan_messages_manager.get_clan_messages(cid, skip=skip, limit=limit)
    return [_format_clan_msg(m) for m in msgs]


def delete_clan_chat_message(actor_data: dict, message_id: str) -> dict:
    aid = str(actor_data["_id"])
    mem = game_database.clans_manager.get_user_membership(aid)
    if not mem:
        raise Network_Exeptions.raise403(details="شما عضو کلن نیستید.")
    msg = game_database.clan_messages_manager.read_message(message_id)
    if not msg or str(msg.get("clan_id")) != str(mem["clan_id"]):
        raise Network_Exeptions.raise404(details="پیام پیدا نشد.")

    role_rank = CLAN_ROLE_RANK.get(str(mem.get("role", "member")), 1)
    if str(msg.get("sender_id")) != aid and role_rank < CLAN_ROLE_RANK["elder"]:
        raise Network_Exeptions.raise403(details="فقط مدیران کلن یا نویسنده پیام مجاز به حذف پیام هستند.")

    game_database.clan_messages_manager.delete_message(message_id, aid)
    game_database.clans_manager.log_audit(str(mem["clan_id"]), aid, "delete_clan_message", message_id)
    return {"deleted": True, "message_id": message_id}
