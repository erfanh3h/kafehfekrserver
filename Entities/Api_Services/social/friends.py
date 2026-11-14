from Entities import Network_Exeptions
from Entities.Database import game_database
from Entities.Api_Services.social.security import (
    check_rate_limit,
    sanitize_text,
    serialize_dt,
    sanitize_public_user_summary,
)


def _attach_user_summaries(user_ids: list[str]) -> dict[str, dict]:
    clean_ids = list({str(u) for u in user_ids if u and not str(u).startswith("bot_")})
    if not clean_ids:
        return {}
    users = game_database.users_manager.read_users(clean_ids)
    pres_map = game_database.presence_manager.get_bulk_presence(clean_ids)
    result: dict[str, dict] = {}
    for u in users:
        uid = str(u["_id"])
        mem = game_database.clans_manager.get_user_membership(uid)
        clan_info = None
        if mem:
            c_doc = game_database.clans_manager.read_clan(str(mem["clan_id"]))
            if c_doc:
                clan_info = dict(c_doc)
                clan_info["role"] = mem.get("role", "member")
        result[uid] = sanitize_public_user_summary(u, pres_map.get(uid), clan_info)
    return result


def search_players(viewer_id: str, query_text: str, limit: int = 25) -> list[dict]:
    vid = str(viewer_id)
    blocked_all = game_database.friends_manager.get_all_block_related_ids(vid)
    excluded = set(blocked_all)
    excluded.add(vid)
    raw_users = game_database.users_manager.search_users(query_text, exclude_ids=excluded, limit=limit)
    uids = [str(u["_id"]) for u in raw_users]
    summaries = _attach_user_summaries(uids)
    friend_ids = set(game_database.friends_manager.get_friend_ids(vid))
    outgoing_reqs = {str(r["to_user_id"]) for r in game_database.friends_manager.get_outgoing_requests(vid)}
    incoming_reqs = {str(r["from_user_id"]) for r in game_database.friends_manager.get_incoming_requests(vid)}

    out = []
    for uid in uids:
        if uid not in summaries:
            continue
        item = dict(summaries[uid])
        item["is_friend"] = uid in friend_ids
        item["request_sent"] = uid in outgoing_reqs
        item["request_received"] = uid in incoming_reqs
        out.append(item)
    return out


def send_friend_request(from_user_id: str, to_user_id: str, message: str = "") -> dict:
    fid, tid = str(from_user_id), str(to_user_id).strip()
    check_rate_limit(fid, "friend_request")
    if not tid or fid == tid:
        raise Network_Exeptions.raise422(details="نمی‌توانید به خودتان درخواست دوستی بدهید.")
    if tid.startswith("bot_") or tid.startswith("test_bot"):
        raise Network_Exeptions.raise422(details="امکان ارسال درخواست دوستی به این بازیکن وجود ندارد.")

    target_user = game_database.users_manager.read_user(tid)
    if not target_user:
        raise Network_Exeptions.raise404(details="بازیکن مورد نظر پیدا نشد.")

    if game_database.friends_manager.is_blocked(fid, tid):
        raise Network_Exeptions.raise403(details="امکان ارسال درخواست دوستی به این بازیکن وجود ندارد.")

    target_priv = target_user.get("privacy") if isinstance(target_user.get("privacy"), dict) else {}
    if not bool(target_priv.get("allow_friend_requests", True)):
        raise Network_Exeptions.raise403(details="این بازیکن دریافت درخواست دوستی را غیرفعال کرده است.")

    if game_database.friends_manager.are_friends(fid, tid):
        raise Network_Exeptions.raise409(details="شما در حال حاضر با این بازیکن دوست هستید.")

    existing_req = game_database.friends_manager.get_pending_request_between(fid, tid)
    if existing_req:
        if str(existing_req.get("from_user_id")) == fid:
            raise Network_Exeptions.raise409(details="درخواست دوستی قبلاً ارسال شده است.")
        # Reverse request already pending -> auto-accept friendship!
        return respond_friend_request(fid, str(existing_req["_id"]), "accept")

    sender = game_database.users_manager.read_user(fid) or {}
    req_doc = game_database.friends_manager.create_friend_request(fid, tid, sanitize_text(message, 140))

    game_database.notifications_manager.create_notification(
        user_id=tid,
        notif_type="friend_request_received",
        title="👥 درخواست دوستی جدید",
        body=f"{sender.get('username', 'بازیکن')} برای شما درخواست دوستی فرستاد.",
        actor_id=fid,
        actor_name=str(sender.get("username", "بازیکن")),
        actor_image=int(sender.get("image", 0) or 0),
        payload={"request_id": req_doc["_id"], "from_user_id": fid},
        category="friend_requests",
    )
    return {
        "request_id": req_doc["_id"],
        "from_user_id": fid,
        "to_user_id": tid,
        "status": "pending",
        "created_at": serialize_dt(req_doc.get("created_at")),
    }


def respond_friend_request(user_id: str, request_id: str, action: str) -> dict:
    uid = str(user_id)
    req = game_database.friends_manager.read_request(request_id)
    if not req or req.get("status") != "pending":
        raise Network_Exeptions.raise404(details="درخواست دوستی یافت نشد یا قبلاً بررسی شده است.")

    act = str(action or "").lower()
    if act == "cancel":
        if str(req.get("from_user_id")) != uid:
            raise Network_Exeptions.raise403(details="شما مجاز به لغو این درخواست نیستید.")
        game_database.friends_manager.update_request_status(request_id, "canceled")
        return {"request_id": request_id, "status": "canceled"}

    if str(req.get("to_user_id")) != uid:
        raise Network_Exeptions.raise403(details="شما مجاز به پاسخ به این درخواست نیستید.")

    from_id = str(req.get("from_user_id"))
    if act == "accept":
        if game_database.friends_manager.is_blocked(uid, from_id):
            game_database.friends_manager.update_request_status(request_id, "rejected")
            raise Network_Exeptions.raise403(details="امکان پذیرش درخواست وجود ندارد.")
        game_database.friends_manager.update_request_status(request_id, "accepted")
        game_database.friends_manager.create_friendship(from_id, uid)
        accepter = game_database.users_manager.read_user(uid) or {}
        game_database.notifications_manager.create_notification(
            user_id=from_id,
            notif_type="friend_request_accepted",
            title="🤝 درخواست دوستی پذیرفته شد",
            body=f"{accepter.get('username', 'بازیکن')} درخواست دوستی شما را پذیرفت!",
            actor_id=uid,
            actor_name=str(accepter.get("username", "بازیکن")),
            actor_image=int(accepter.get("image", 0) or 0),
            payload={"friend_id": uid},
            category="friend_requests",
        )
        return {"request_id": request_id, "status": "accepted", "friend_id": from_id}

    if act == "reject":
        game_database.friends_manager.update_request_status(request_id, "rejected")
        return {"request_id": request_id, "status": "rejected"}

    raise Network_Exeptions.raise422(details="عملیات نامعتبر است.")


def remove_friend(user_id: str, friend_id: str) -> dict:
    uid, fid = str(user_id), str(friend_id)
    if not game_database.friends_manager.are_friends(uid, fid):
        raise Network_Exeptions.raise404(details="این بازیکن در لیست دوستان شما نیست.")
    game_database.friends_manager.remove_friendship(uid, fid)
    return {"removed": True, "friend_id": fid}


def get_friends_list(user_id: str) -> list[dict]:
    uid = str(user_id)
    f_ids = game_database.friends_manager.get_friend_ids(uid)
    if not f_ids:
        return []
    summaries = _attach_user_summaries(f_ids)
    status_order = {"in_game": 0, "in_lobby": 1, "in_queue": 2, "online": 3, "away": 4, "offline": 5}
    items = [summaries[fid] for fid in f_ids if fid in summaries]
    items.sort(key=lambda x: (status_order.get(str(x.get("status", "offline")), 5), -int(x.get("score", 0))))
    return items


def get_friend_requests(user_id: str) -> dict:
    uid = str(user_id)
    inc = game_database.friends_manager.get_incoming_requests(uid)
    out = game_database.friends_manager.get_outgoing_requests(uid)
    all_uids = [str(r["from_user_id"]) for r in inc] + [str(r["to_user_id"]) for r in out]
    summaries = _attach_user_summaries(all_uids)

    incoming_list = []
    for r in inc:
        fid = str(r["from_user_id"])
        incoming_list.append(
            {
                "request_id": str(r["_id"]),
                "from_user": summaries.get(fid, {"user_id": fid, "username": "بازیکن", "image": 0}),
                "message": str(r.get("message", "")),
                "created_at": serialize_dt(r.get("created_at")),
            }
        )

    outgoing_list = []
    for r in out:
        tid = str(r["to_user_id"])
        outgoing_list.append(
            {
                "request_id": str(r["_id"]),
                "to_user": summaries.get(tid, {"user_id": tid, "username": "بازیکن", "image": 0}),
                "message": str(r.get("message", "")),
                "created_at": serialize_dt(r.get("created_at")),
            }
        )

    return {"incoming": incoming_list, "outgoing": outgoing_list}


def get_recently_played_and_suggestions(user_id: str, limit: int = 15) -> dict:
    uid = str(user_id)
    blocked = game_database.friends_manager.get_all_block_related_ids(uid)
    my_friends = set(game_database.friends_manager.get_friend_ids(uid))
    outgoing_reqs = {str(r["to_user_id"]) for r in game_database.friends_manager.get_outgoing_requests(uid)}

    recent_ids: list[str] = []
    seen: set[str] = {uid} | blocked
    try:
        games = game_database.game_play_history_manager.read_user_games_histories(uid)
        for g in games[:30]:
            for p_id in g.get("user_ids", []):
                ps = str(p_id)
                if ps and not ps.startswith("bot_") and not ps.startswith("test_bot") and ps not in seen:
                    seen.add(ps)
                    recent_ids.append(ps)
                    if len(recent_ids) >= limit:
                        break
            if len(recent_ids) >= limit:
                break
    except Exception:
        pass

    # Mutual friend suggestions
    mutual_counts: dict[str, int] = {}
    for fid in list(my_friends)[:20]:
        for fof in game_database.friends_manager.get_friend_ids(fid):
            if fof != uid and fof not in my_friends and fof not in blocked and not fof.startswith("bot_"):
                mutual_counts[fof] = mutual_counts.get(fof, 0) + 1

    suggested_ids = [
        k for k, _ in sorted(mutual_counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]
    for rid in recent_ids:
        if rid not in my_friends and rid not in suggested_ids and len(suggested_ids) < limit:
            suggested_ids.append(rid)

    summaries = _attach_user_summaries(list(set(recent_ids + suggested_ids)))
    recent_out = []
    for rid in recent_ids:
        if rid in summaries:
            d = dict(summaries[rid])
            d["is_friend"] = rid in my_friends
            d["request_sent"] = rid in outgoing_reqs
            recent_out.append(d)

    suggested_out = []
    for sid in suggested_ids:
        if sid in summaries:
            d = dict(summaries[sid])
            d["mutual_friends"] = mutual_counts.get(sid, 0)
            d["request_sent"] = sid in outgoing_reqs
            suggested_out.append(d)

    return {"recently_played": recent_out, "suggestions": suggested_out}
