from datetime import datetime, timedelta
from Commons.static_functions import create_random_name
from Entities import Network_Exeptions
from Entities.Database import game_database
from Entities.Database.social.clans_collection import (
    CLAN_ROLE_RANK,
    CLAN_ROLE_FA,
    CLAN_CREATION_COIN_COST,
    DEFAULT_MAX_CLAN_MEMBERS,
)
from Entities.Api_Services.social.security import (
    check_rate_limit,
    sanitize_text,
    validate_safe_name,
    validate_clan_tag,
    calculate_player_level,
    serialize_dt,
    sanitize_public_user_summary,
)


WEEKLY_CLAN_CHALLENGES = [
    {
        "id": "weekly_20_wins",
        "title": "۲۰ پیروزی هفتگی کلن",
        "desc": "اعضای کلن در مجموع ۲۰ پیروزی در این هفته کسب کنند.",
        "target": 20,
        "reward_clan_xp": 150,
    },
    {
        "id": "weekly_300_pts",
        "title": "۳۰۰ امتیاز مشارکت هفتگی",
        "desc": "اعضای کلن در این هفته ۳۰۰ امتیاز مشارکت جمع‌آوری کنند.",
        "target": 300,
        "reward_clan_xp": 250,
    },
]


def _serialize_clan(clan_doc: dict | None, viewer_membership: dict | None = None) -> dict:
    if not clan_doc:
        return {}
    cid = str(clan_doc["_id"])
    weekly_score = int(clan_doc.get("weekly_score", 0) or 0)
    total_wins = int(clan_doc.get("total_wins", 0) or 0)
    challenges_progress = [
        {
            **WEEKLY_CLAN_CHALLENGES[0],
            "progress": min(WEEKLY_CLAN_CHALLENGES[0]["target"], total_wins),
            "completed": total_wins >= WEEKLY_CLAN_CHALLENGES[0]["target"],
        },
        {
            **WEEKLY_CLAN_CHALLENGES[1],
            "progress": min(WEEKLY_CLAN_CHALLENGES[1]["target"], weekly_score),
            "completed": weekly_score >= WEEKLY_CLAN_CHALLENGES[1]["target"],
        },
    ]
    out = {
        "clan_id": cid,
        "_id": cid,
        "name": str(clan_doc.get("name", "")),
        "tag": str(clan_doc.get("tag", "")),
        "emblem_id": int(clan_doc.get("emblem_id", 1) or 1),
        "description": str(clan_doc.get("description", "")),
        "language": str(clan_doc.get("language", "fa")),
        "join_type": str(clan_doc.get("join_type", "open")),
        "min_score": int(clan_doc.get("min_score", 0) or 0),
        "min_level": int(clan_doc.get("min_level", 1) or 1),
        "leader_id": str(clan_doc.get("leader_id", "")),
        "clan_level": int(clan_doc.get("clan_level", 1) or 1),
        "clan_xp": int(clan_doc.get("clan_xp", 0) or 0),
        "member_count": int(clan_doc.get("member_count", 1) or 1),
        "max_members": int(clan_doc.get("max_members", DEFAULT_MAX_CLAN_MEMBERS) or DEFAULT_MAX_CLAN_MEMBERS),
        "clan_score": int(clan_doc.get("clan_score", 0) or 0),
        "weekly_score": weekly_score,
        "monthly_score": int(clan_doc.get("monthly_score", 0) or 0),
        "total_wins": total_wins,
        "total_matches": int(clan_doc.get("total_matches", 0) or 0),
        "achievements": list(clan_doc.get("achievements", []) or []),
        "weekly_challenges": challenges_progress,
        "created_at": serialize_dt(clan_doc.get("created_at")),
        "my_role": str(viewer_membership.get("role", "")) if viewer_membership else "",
    }
    return out


def _post_clan_system_message(clan_id: str, text: str, metadata: dict | None = None):
    try:
        game_database.clan_messages_manager.create_message(
            clan_id=str(clan_id),
            sender_id="system",
            sender_name="سیستم کلن",
            sender_image=0,
            sender_role="system",
            text=text,
            msg_type="system",
            metadata=metadata or {},
        )
    except Exception:
        pass


def create_clan(
    user_data: dict,
    name: str,
    tag: str,
    emblem_id: int = 1,
    description: str = "",
    language: str = "fa",
    join_type: str = "open",
    min_score: int = 0,
    min_level: int = 1,
) -> dict:
    uid = str(user_data["_id"])
    check_rate_limit(uid, "clan_create")

    if game_database.clans_manager.get_user_membership(uid) is not None:
        raise Network_Exeptions.raise409(details="شما در حال حاضر عضو یک کلن هستید. ابتدا از کلن فعلی خارج شوید.")

    clean_name = validate_safe_name(name, min_len=3, max_len=24, field_label="نام کلن")
    clean_tag = validate_clan_tag(tag)

    if game_database.clans_manager.read_clan_by_name(clean_name) is not None:
        raise Network_Exeptions.raise409(details="این نام کلن قبلاً ثبت شده است.")
    if game_database.clans_manager.read_clan_by_tag(clean_tag) is not None:
        raise Network_Exeptions.raise409(details="این تگ کلن قبلاً ثبت شده است.")

    user_coin = int(user_data.get("coin", 0) or 0)
    if user_coin < CLAN_CREATION_COIN_COST:
        raise Network_Exeptions.raise422(
            details=f"برای ساخت کلن به {CLAN_CREATION_COIN_COST} سکه نیاز دارید."
        )

    # Deduct coin cost atomically via existing users_manager
    game_database.users_manager.update_user(uid, coin=user_coin - CLAN_CREATION_COIN_COST)

    clan_doc = game_database.clans_manager.create_clan(
        leader_id=uid,
        name=clean_name,
        tag=clean_tag,
        emblem_id=emblem_id,
        description=sanitize_text(description, 280),
        language=language,
        join_type=join_type,
        min_score=min_score,
        min_level=min_level,
    )
    _post_clan_system_message(
        clan_doc["_id"],
        f"🏰 کلن «{clean_name}» ({clean_tag}) توسط {user_data.get('username', 'بازیکن')} تاسیس شد!",
    )
    mem = game_database.clans_manager.get_user_membership(uid)
    return _serialize_clan(clan_doc, mem)


def search_clans_directory(
    viewer_id: str,
    query_text: str = "",
    join_type: str = "",
    language: str = "",
    only_joinable: bool = False,
    sort_by: str = "clan_score",
    skip: int = 0,
    limit: int = 30,
) -> list[dict]:
    my_mem = game_database.clans_manager.get_user_membership(viewer_id)
    docs = game_database.clans_manager.search_clans(
        query_text=query_text,
        join_type=join_type,
        language=language,
        only_joinable=only_joinable,
        sort_by=sort_by,
        skip=skip,
        limit=limit,
    )
    out = []
    for d in docs:
        vm = my_mem if (my_mem and str(my_mem.get("clan_id")) == str(d["_id"])) else None
        out.append(_serialize_clan(d, vm))
    return out


def get_clan_details(viewer_id: str, clan_id: str) -> dict:
    vid = str(viewer_id)
    cid = str(clan_id or "").strip()
    if not cid:
        my_mem = game_database.clans_manager.get_user_membership(vid)
        if not my_mem:
            return {"clan": None, "members": [], "join_requests": []}
        cid = str(my_mem["clan_id"])

    clan_doc = game_database.clans_manager.read_clan(cid)
    if not clan_doc:
        raise Network_Exeptions.raise404(details="کلن مورد نظر پیدا نشد.")

    my_mem = game_database.clans_manager.get_user_membership(vid)
    in_this_clan = my_mem is not None and str(my_mem.get("clan_id")) == cid
    raw_members = game_database.clans_manager.get_clan_members(cid)
    uids = [str(m["user_id"]) for m in raw_members]
    users_list = game_database.users_manager.read_users(uids)
    users_map = {str(u["_id"]): u for u in users_list}
    pres_map = game_database.presence_manager.get_bulk_presence(uids)

    members_out = []
    for m in raw_members:
        mid = str(m["user_id"])
        u_doc = users_map.get(mid, {"_id": mid, "username": "بازیکن", "image": 0, "score": 0, "xp": 0})
        summary = sanitize_public_user_summary(u_doc, pres_map.get(mid))
        summary.update(
            {
                "role": str(m.get("role", "member")),
                "role_title": CLAN_ROLE_FA.get(str(m.get("role", "member")), "عضو"),
                "role_rank": int(m.get("role_rank", 1)),
                "contribution_score": int(m.get("contribution_score", 0) or 0),
                "weekly_contribution": int(m.get("weekly_contribution", 0) or 0),
                "monthly_contribution": int(m.get("monthly_contribution", 0) or 0),
                "contribution_xp": int(m.get("contribution_xp", 0) or 0),
                "matches_played": int(m.get("matches_played", 0) or 0),
                "matches_won": int(m.get("matches_won", 0) or 0),
                "joined_at": serialize_dt(m.get("joined_at")),
            }
        )
        members_out.append(summary)

    join_requests_out = []
    audit_logs_out = []
    if in_this_clan and CLAN_ROLE_RANK.get(str(my_mem.get("role", "member")), 1) >= CLAN_ROLE_RANK["elder"]:
        raw_reqs = game_database.clans_manager.get_pending_join_requests(cid)
        req_uids = [str(r["user_id"]) for r in raw_reqs]
        req_users = {str(u["_id"]): u for u in game_database.users_manager.read_users(req_uids)}
        for r in raw_reqs:
            ruid = str(r["user_id"])
            ru = req_users.get(ruid, {"_id": ruid, "username": "بازیکن", "image": 0, "score": 0, "xp": 0})
            join_requests_out.append(
                {
                    "request_id": str(r["_id"]),
                    "user": sanitize_public_user_summary(ru),
                    "message": str(r.get("message", "")),
                    "created_at": serialize_dt(r.get("created_at")),
                }
            )
        audit_logs_out = [
            {
                "action": str(a.get("action", "")),
                "actor_id": str(a.get("actor_id", "")),
                "target_id": str(a.get("target_id", "")),
                "details": a.get("details", {}),
                "created_at": serialize_dt(a.get("created_at")),
            }
            for a in game_database.clans_manager.get_audit_logs(cid, limit=25)
        ]

    return {
        "clan": _serialize_clan(clan_doc, my_mem if in_this_clan else None),
        "members": members_out,
        "join_requests": join_requests_out,
        "audit_logs": audit_logs_out,
    }


def join_or_request_clan(user_data: dict, clan_id: str, message: str = "") -> dict:
    uid = str(user_data["_id"])
    cid = str(clan_id).strip()
    if game_database.clans_manager.get_user_membership(uid) is not None:
        raise Network_Exeptions.raise409(details="شما در حال حاضر عضو یک کلن هستید.")

    clan = game_database.clans_manager.read_clan(cid)
    if not clan:
        raise Network_Exeptions.raise404(details="کلن پیدا نشد.")

    max_m = int(clan.get("max_members", DEFAULT_MAX_CLAN_MEMBERS))
    if int(clan.get("member_count", 0)) >= max_m:
        raise Network_Exeptions.raise422(details="ظرفیت این کلن تکمیل است.")

    u_score = int(user_data.get("score", 0) or 0)
    u_lvl = calculate_player_level(int(user_data.get("xp", 0) or 0))
    if u_score < int(clan.get("min_score", 0) or 0):
        raise Network_Exeptions.raise422(details="امتیاز شما کمتر از حداقل امتیاز کلن است.")
    if u_lvl < int(clan.get("min_level", 1) or 1):
        raise Network_Exeptions.raise422(details="سطح شما کمتر از حداقل سطح مورد نیاز کلن است.")

    j_type = str(clan.get("join_type", "open"))
    if j_type == "invite_only":
        raise Network_Exeptions.raise403(details="عضویت در این کلن فقط با دعوت‌نامه امکان‌پذیر است.")

    if j_type == "request":
        req = game_database.clans_manager.create_join_request(cid, uid, sanitize_text(message, 140))
        # Notify leader & co-leaders
        for m in game_database.clans_manager.get_clan_members(cid):
            if CLAN_ROLE_RANK.get(str(m.get("role", "member")), 1) >= CLAN_ROLE_RANK["elder"]:
                game_database.notifications_manager.create_notification(
                    user_id=str(m["user_id"]),
                    notif_type="clan_join_request",
                    title="🛡️ درخواست عضویت در کلن",
                    body=f"{user_data.get('username', 'بازیکن')} درخواست عضویت در کلن را ارسال کرد.",
                    actor_id=uid,
                    actor_name=str(user_data.get("username", "بازیکن")),
                    actor_image=int(user_data.get("image", 0) or 0),
                    payload={"clan_id": cid, "request_id": req["_id"]},
                    category="clan_events",
                )
        return {"status": "requested", "request_id": req["_id"], "clan_id": cid}

    # Open clan -> join immediately
    ok, reason = game_database.clans_manager.add_member_atomic(cid, uid, "member")
    if not ok:
        if reason == "clan_full":
            raise Network_Exeptions.raise422(details="ظرفیت کلن تکمیل است.")
        raise Network_Exeptions.raise409(details="امکان عضویت در کلن وجود ندارد.")

    _post_clan_system_message(cid, f"🎉 {user_data.get('username', 'بازیکن')} به کلن پیوست!")
    return {"status": "joined", "clan_id": cid}


def respond_clan_join_request(actor_data: dict, request_id: str, action: str) -> dict:
    aid = str(actor_data["_id"])
    req = game_database.clans_manager.read_join_request(request_id)
    if not req or req.get("status") != "pending":
        raise Network_Exeptions.raise404(details="درخواست عضویت پیدا نشد یا قبلاً بررسی شده است.")

    cid = str(req["clan_id"])
    target_uid = str(req["user_id"])
    actor_mem = game_database.clans_manager.get_user_membership(aid)
    if not actor_mem or str(actor_mem.get("clan_id")) != cid:
        raise Network_Exeptions.raise403(details="شما عضو این کلن نیستید.")
    if CLAN_ROLE_RANK.get(str(actor_mem.get("role", "member")), 1) < CLAN_ROLE_RANK["elder"]:
        raise Network_Exeptions.raise403(details="فقط رهبر، قائم‌مقام یا ارشد مجاز به بررسی درخواست عضویت هستند.")

    act = str(action or "").lower()
    if act == "reject":
        game_database.clans_manager.update_join_request_status(request_id, "rejected", aid)
        game_database.clans_manager.log_audit(cid, aid, "reject_join_request", target_uid)
        return {"request_id": request_id, "status": "rejected"}

    if act == "accept":
        ok, reason = game_database.clans_manager.add_member_atomic(cid, target_uid, "member")
        if not ok:
            game_database.clans_manager.update_join_request_status(request_id, "rejected", aid)
            if reason == "clan_full":
                raise Network_Exeptions.raise422(details="ظرفیت کلن تکمیل است.")
            raise Network_Exeptions.raise409(details="این بازیکن قبلاً عضو کلن دیگری شده است.")
        game_database.clans_manager.update_join_request_status(request_id, "accepted", aid)
        game_database.clans_manager.log_audit(cid, aid, "accept_join_request", target_uid)

        target_u = game_database.users_manager.read_user(target_uid) or {}
        clan = game_database.clans_manager.read_clan(cid) or {}
        _post_clan_system_message(
            cid,
            f"🎉 درخواست عضویت {target_u.get('username', 'بازیکن')} توسط {actor_data.get('username', 'مدیر')} پذیرفته شد!",
        )
        game_database.notifications_manager.create_notification(
            user_id=target_uid,
            notif_type="clan_join_accepted",
            title="🏰 عضویت در کلن تایید شد",
            body=f"شما به کلن «{clan.get('name', '')}» پیوستید!",
            actor_id=aid,
            actor_name=str(actor_data.get("username", "")),
            actor_image=int(actor_data.get("image", 0) or 0),
            payload={"clan_id": cid},
            category="clan_events",
        )
        return {"request_id": request_id, "status": "accepted", "clan_id": cid, "user_id": target_uid}

    raise Network_Exeptions.raise422(details="عملیات نامعتبر است.")


def invite_player_to_clan(actor_data: dict, target_user_id: str) -> dict:
    aid = str(actor_data["_id"])
    tid = str(target_user_id).strip()
    actor_mem = game_database.clans_manager.get_user_membership(aid)
    if not actor_mem:
        raise Network_Exeptions.raise403(details="شما عضو هیچ کلنی نیستید.")
    if CLAN_ROLE_RANK.get(str(actor_mem.get("role", "member")), 1) < CLAN_ROLE_RANK["elder"]:
        raise Network_Exeptions.raise403(details="فقط رهبر، قائم‌مقام و ارشد می‌توانند بازیکن دعوت کنند.")

    cid = str(actor_mem["clan_id"])
    if game_database.clans_manager.get_user_membership(tid) is not None:
        raise Network_Exeptions.raise409(details="این بازیکن در حال حاضر عضو یک کلن است.")
    if game_database.friends_manager.is_blocked(aid, tid):
        raise Network_Exeptions.raise403(details="امکان دعوت این بازیکن وجود ندارد.")

    target_u = game_database.users_manager.read_user(tid)
    if not target_u:
        raise Network_Exeptions.raise404(details="بازیکن مورد نظر یافت نشد.")

    clan = game_database.clans_manager.read_clan(cid) or {}
    inv = game_database.clans_manager.create_clan_invitation(cid, aid, tid)
    game_database.clans_manager.log_audit(cid, aid, "invite_player", tid)
    game_database.notifications_manager.create_notification(
        user_id=tid,
        notif_type="clan_invitation_received",
        title="🛡️ دعوت‌نامه عضویت در کلن",
        body=f"{actor_data.get('username', 'بازیکن')} شما را به کلن «{clan.get('name', '')}» دعوت کرد.",
        actor_id=aid,
        actor_name=str(actor_data.get("username", "")),
        actor_image=int(actor_data.get("image", 0) or 0),
        payload={"invite_id": inv["_id"], "clan_id": cid, "clan_name": clan.get("name", "")},
        category="clan_invitations",
    )
    return {
        "invite_id": str(inv["_id"]),
        "clan_id": cid,
        "to_user_id": tid,
        "status": "pending",
    }


def respond_clan_invitation(user_data: dict, invite_id: str, action: str) -> dict:
    uid = str(user_data["_id"])
    inv = game_database.clans_manager.read_clan_invitation(invite_id)
    if not inv or inv.get("status") != "pending":
        raise Network_Exeptions.raise404(details="دعوت‌نامه کلن پیدا نشد یا منقضی شده است.")

    cid = str(inv["clan_id"])
    act = str(action or "").lower()
    if act == "cancel":
        actor_mem = game_database.clans_manager.get_user_membership(uid)
        if str(inv.get("from_user_id")) != uid and (
            not actor_mem
            or str(actor_mem.get("clan_id")) != cid
            or CLAN_ROLE_RANK.get(str(actor_mem.get("role", "member")), 1) < CLAN_ROLE_RANK["co_leader"]
        ):
            raise Network_Exeptions.raise403(details="مجاز به لغو این دعوت‌نامه نیستید.")
        game_database.clans_manager.update_clan_invitation_status(invite_id, "canceled")
        return {"invite_id": invite_id, "status": "canceled"}

    if str(inv.get("to_user_id")) != uid:
        raise Network_Exeptions.raise403(details="این دعوت‌نامه متعلق به شما نیست.")

    if act == "reject":
        game_database.clans_manager.update_clan_invitation_status(invite_id, "rejected")
        return {"invite_id": invite_id, "status": "rejected"}

    if act == "accept":
        ok, reason = game_database.clans_manager.add_member_atomic(cid, uid, "member")
        if not ok:
            if reason == "clan_full":
                raise Network_Exeptions.raise422(details="ظرفیت کلن تکمیل است.")
            raise Network_Exeptions.raise409(details="شما در حال حاضر عضو کلن دیگری هستید.")
        game_database.clans_manager.update_clan_invitation_status(invite_id, "accepted")
        _post_clan_system_message(cid, f"🎉 {user_data.get('username', 'بازیکن')} با پذیرش دعوت‌نامه به کلن پیوست!")
        return {"invite_id": invite_id, "status": "accepted", "clan_id": cid}

    raise Network_Exeptions.raise422(details="عملیات نامعتبر است.")


def leave_clan(user_data: dict) -> dict:
    uid = str(user_data["_id"])
    mem = game_database.clans_manager.get_user_membership(uid)
    if not mem:
        raise Network_Exeptions.raise404(details="شما عضو هیچ کلنی نیستید.")
    cid = str(mem["clan_id"])
    role = str(mem.get("role", "member"))
    all_members = game_database.clans_manager.get_clan_members(cid)

    if role == "leader":
        if len(all_members) > 1:
            raise Network_Exeptions.raise422(
                details="رهبر کلن قبل از خروج باید رهبری را به عضو دیگری منتقل کند یا کلن را منحل نماید."
            )
        # Sole member leaving -> disband clan
        game_database.clans_manager.disband_clan(cid, uid)
        return {"left": True, "disbanded": True, "clan_id": cid}

    game_database.clans_manager.remove_member(cid, uid)
    _post_clan_system_message(cid, f"👋 {user_data.get('username', 'بازیکن')} از کلن خارج شد.")
    return {"left": True, "disbanded": False, "clan_id": cid}


def kick_clan_member(actor_data: dict, target_user_id: str) -> dict:
    aid = str(actor_data["_id"])
    tid = str(target_user_id).strip()
    if aid == tid:
        raise Network_Exeptions.raise422(details="برای خروج از کلن از گزینه ترک کلن استفاده کنید.")
    actor_mem = game_database.clans_manager.get_user_membership(aid)
    target_mem = game_database.clans_manager.get_user_membership(tid)
    if not actor_mem or not target_mem or str(actor_mem.get("clan_id")) != str(target_mem.get("clan_id")):
        raise Network_Exeptions.raise404(details="بازیکن مورد نظر در کلن شما نیست.")

    cid = str(actor_mem["clan_id"])
    actor_rank = CLAN_ROLE_RANK.get(str(actor_mem.get("role", "member")), 1)
    target_rank = CLAN_ROLE_RANK.get(str(target_mem.get("role", "member")), 1)
    if actor_rank < CLAN_ROLE_RANK["elder"] or actor_rank <= target_rank:
        raise Network_Exeptions.raise403(details="شما اجازه اخراج هم‌کلنی با درجه هم‌سطح یا بالاتر را ندارید.")

    target_u = game_database.users_manager.read_user(tid) or {}
    game_database.clans_manager.remove_member(cid, tid)
    game_database.clans_manager.log_audit(cid, aid, "kick_member", tid)
    _post_clan_system_message(
        cid,
        f"🚫 {target_u.get('username', 'بازیکن')} توسط {actor_data.get('username', 'مدیر')} از کلن اخراج شد.",
    )
    return {"kicked": True, "user_id": tid, "clan_id": cid}


def change_member_role(actor_data: dict, target_user_id: str, new_role: str) -> dict:
    aid = str(actor_data["_id"])
    tid = str(target_user_id).strip()
    r_new = str(new_role or "").strip().lower()
    if r_new == "leader":
        return transfer_clan_leadership(actor_data, tid)
    if r_new not in ("member", "elder", "co_leader"):
        raise Network_Exeptions.raise422(details="نقش انتخاب‌شده معتبر نیست.")

    actor_mem = game_database.clans_manager.get_user_membership(aid)
    target_mem = game_database.clans_manager.get_user_membership(tid)
    if not actor_mem or not target_mem or str(actor_mem.get("clan_id")) != str(target_mem.get("clan_id")):
        raise Network_Exeptions.raise404(details="بازیکن مورد نظر در کلن شما نیست.")

    cid = str(actor_mem["clan_id"])
    actor_rank = CLAN_ROLE_RANK.get(str(actor_mem.get("role", "member")), 1)
    target_rank = CLAN_ROLE_RANK.get(str(target_mem.get("role", "member")), 1)
    new_rank = CLAN_ROLE_RANK[r_new]

    # Only Leader or Co-Leader can promote/demote, and only strictly below their own rank
    if actor_rank < CLAN_ROLE_RANK["co_leader"] or actor_rank <= target_rank or actor_rank <= new_rank:
        raise Network_Exeptions.raise403(details="شما دسترسی کافی برای تغییر درجه این عضو را ندارید.")

    game_database.clans_manager.set_member_role(cid, tid, r_new)
    game_database.clans_manager.log_audit(cid, aid, "change_role", tid, {"new_role": r_new})
    target_u = game_database.users_manager.read_user(tid) or {}
    role_fa = CLAN_ROLE_FA.get(r_new, r_new)
    _post_clan_system_message(cid, f"🎖️ درجه {target_u.get('username', 'بازیکن')} به «{role_fa}» تغییر یافت.")
    game_database.notifications_manager.create_notification(
        user_id=tid,
        notif_type="clan_role_changed",
        title="🎖️ تغییر درجه در کلن",
        body=f"درجه شما در کلن به «{role_fa}» تغییر یافت.",
        actor_id=aid,
        actor_name=str(actor_data.get("username", "")),
        actor_image=int(actor_data.get("image", 0) or 0),
        payload={"clan_id": cid, "new_role": r_new},
        category="clan_events",
    )
    return {"clan_id": cid, "user_id": tid, "new_role": r_new, "role_title": role_fa}


def transfer_clan_leadership(actor_data: dict, new_leader_id: str) -> dict:
    aid = str(actor_data["_id"])
    nid = str(new_leader_id).strip()
    if aid == nid:
        raise Network_Exeptions.raise422(details="شما در حال حاضر رهبر کلن هستید.")
    actor_mem = game_database.clans_manager.get_user_membership(aid)
    target_mem = game_database.clans_manager.get_user_membership(nid)
    if not actor_mem or str(actor_mem.get("role")) != "leader":
        raise Network_Exeptions.raise403(details="فقط رهبر کلن می‌تواند رهبری را واگذار کند.")
    if not target_mem or str(target_mem.get("clan_id")) != str(actor_mem.get("clan_id")):
        raise Network_Exeptions.raise404(details="بازیکن انتخاب‌شده عضو کلن شما نیست.")

    cid = str(actor_mem["clan_id"])
    game_database.clans_manager.transfer_leadership(cid, aid, nid)
    target_u = game_database.users_manager.read_user(nid) or {}
    _post_clan_system_message(
        cid,
        f"👑 رهبری کلن توسط {actor_data.get('username', 'رهبر')} به {target_u.get('username', 'بازیکن')} واگذار شد!",
    )
    return {"clan_id": cid, "new_leader_id": nid}


def disband_clan(actor_data: dict) -> dict:
    aid = str(actor_data["_id"])
    actor_mem = game_database.clans_manager.get_user_membership(aid)
    if not actor_mem or str(actor_mem.get("role")) != "leader":
        raise Network_Exeptions.raise403(details="فقط رهبر کلن مجاز به انحلال کلن است.")
    cid = str(actor_mem["clan_id"])
    game_database.clans_manager.disband_clan(cid, aid)
    return {"disbanded": True, "clan_id": cid}


def update_clan_settings(actor_data: dict, updates: dict) -> dict:
    aid = str(actor_data["_id"])
    actor_mem = game_database.clans_manager.get_user_membership(aid)
    if not actor_mem or CLAN_ROLE_RANK.get(str(actor_mem.get("role", "member")), 1) < CLAN_ROLE_RANK["co_leader"]:
        raise Network_Exeptions.raise403(details="فقط رهبر و قائم‌مقام می‌توانند تنظیمات کلن را ویرایش کنند.")
    cid = str(actor_mem["clan_id"])
    updated = game_database.clans_manager.update_clan_settings(cid, updates)
    game_database.clans_manager.log_audit(cid, aid, "update_settings", cid, updates)
    return _serialize_clan(updated, actor_mem)


def create_clan_friendly_challenge(actor_data: dict, game_type: str = "Ludo", player_count: int = 2) -> dict:
    aid = str(actor_data["_id"])
    mem = game_database.clans_manager.get_user_membership(aid)
    if not mem:
        raise Network_Exeptions.raise403(details="ابتدا وارد یک کلن شوید.")
    cid = str(mem["clan_id"])
    now = datetime.now()
    ch_id = f"cchal_{create_random_name()}"
    doc = {
        "_id": ch_id,
        "clan_id": cid,
        "creator_id": aid,
        "creator_name": str(actor_data.get("username", "بازیکن")),
        "game_type": str(game_type or "Ludo"),
        "player_count": max(2, min(int(player_count or 2), 4)),
        "status": "open",
        "created_at": now,
        "expires_at": now + timedelta(minutes=10),
    }
    game_database.clans_manager.challenges.insert_one(doc)
    _post_clan_system_message(
        cid,
        f"⚔️ {actor_data.get('username', 'بازیکن')} یک چالش دوستانه «{game_type}» در کلن ایجاد کرد!",
        metadata={"challenge_id": ch_id, "game_type": game_type, "player_count": doc["player_count"]},
    )
    return {
        "challenge_id": ch_id,
        "clan_id": cid,
        "game_type": doc["game_type"],
        "player_count": doc["player_count"],
        "status": "open",
    }
