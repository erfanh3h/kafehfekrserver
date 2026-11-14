import pymongo
from Entities.Database import game_database
from Entities.Api_Services.social.security import sanitize_public_user_summary
from Entities.Api_Services.social.clans import _serialize_clan


def get_social_leaderboard(
    viewer_id: str,
    board_type: str = "global_score",
    game_type: str = "",
    clan_id: str = "",
    limit: int = 30,
) -> list[dict]:
    vid = str(viewer_id)
    lim = max(1, min(int(limit or 30), 50))
    bt = str(board_type or "global_score").lower()

    if bt in ("clans", "clans_weekly", "clans_monthly"):
        sort_key = "clan_score"
        if bt == "clans_weekly":
            sort_key = "weekly_score"
        elif bt == "clans_monthly":
            sort_key = "monthly_score"
        docs = game_database.clans_manager.search_clans(sort_by=sort_key, limit=lim)
        out = []
        for idx, d in enumerate(docs, 1):
            row = _serialize_clan(d)
            row["rank"] = idx
            row["value"] = int(d.get(sort_key, 0) or 0)
            out.append(row)
        return out

    if bt == "clan_members":
        cid = str(clan_id or "").strip()
        if not cid:
            mem = game_database.clans_manager.get_user_membership(vid)
            cid = str(mem["clan_id"]) if mem else ""
        if not cid:
            return []
        members = game_database.clans_manager.get_clan_members(cid)
        uids = [str(m["user_id"]) for m in members]
        users_map = {str(u["_id"]): u for u in game_database.users_manager.read_users(uids)}
        pres_map = game_database.presence_manager.get_bulk_presence(uids)
        out = []
        for idx, m in enumerate(members, 1):
            uid = str(m["user_id"])
            u_doc = users_map.get(uid, {"_id": uid, "username": "بازیکن", "image": 0, "score": 0, "xp": 0})
            row = sanitize_public_user_summary(u_doc, pres_map.get(uid))
            row["rank"] = idx
            row["role"] = str(m.get("role", "member"))
            row["contribution_score"] = int(m.get("contribution_score", 0) or 0)
            row["weekly_contribution"] = int(m.get("weekly_contribution", 0) or 0)
            row["value"] = row["contribution_score"]
            out.append(row)
        return out

    if bt == "friends":
        f_ids = list(set(game_database.friends_manager.get_friend_ids(vid) + [vid]))
        users_list = game_database.users_manager.read_users(f_ids)
        pres_map = game_database.presence_manager.get_bulk_presence(f_ids)
        users_list.sort(key=lambda u: int(u.get("score", 0) or 0), reverse=True)
        out = []
        for idx, u in enumerate(users_list[:lim], 1):
            uid = str(u["_id"])
            row = sanitize_public_user_summary(u, pres_map.get(uid))
            row["rank"] = idx
            row["value"] = int(u.get("score", 0) or 0)
            out.append(row)
        return out

    if bt == "game" and game_type:
        gt_key = f"{str(game_type).strip().lower()}_win"
        q = {gt_key: {"$gt": 0}, "_id": {"$ne": "3goBRU", "$not": {"$regex": "^bot_|^test_bot"}}}
        cursor = (
            game_database.user_history_manager.collection.find(q, {gt_key: 1})
            .sort([(gt_key, pymongo.DESCENDING)])
            .limit(lim)
        )
        hist_rows = list(cursor)
        uids = [str(r["_id"]) for r in hist_rows]
        users_map = {str(u["_id"]): u for u in game_database.users_manager.read_users(uids)}
        pres_map = game_database.presence_manager.get_bulk_presence(uids)
        out = []
        for idx, h in enumerate(hist_rows, 1):
            uid = str(h["_id"])
            if uid not in users_map:
                continue
            row = sanitize_public_user_summary(users_map[uid], pres_map.get(uid))
            row["rank"] = idx
            row["value"] = int(h.get(gt_key, 0) or 0)
            row["game_type"] = game_type
            out.append(row)
        return out

    if bt == "global_wins":
        from Entities.Api_Services import user as user_service
        win_rows = user_service.get_ranking_users_by_win()
        out = []
        for idx, item in enumerate(win_rows[:lim], 1):
            u_doc = item.get("user_data", {})
            uid = str(u_doc.get("_id", ""))
            row = sanitize_public_user_summary(u_doc, game_database.presence_manager.get_presence(uid))
            row["rank"] = idx
            row["value"] = int(item.get("win", 0) or 0)
            out.append(row)
        return out

    # Default: global_score (also used for weekly/monthly player score rankings)
    score_docs = list(game_database.users_manager.read_ranking_users_by_score())
    uids = [str(u["_id"]) for u in score_docs]
    pres_map = game_database.presence_manager.get_bulk_presence(uids)
    out = []
    for idx, u in enumerate(score_docs[:lim], 1):
        uid = str(u["_id"])
        row = sanitize_public_user_summary(u, pres_map.get(uid))
        row["rank"] = idx
        row["value"] = int(u.get("score", 0) or 0)
        out.append(row)
    return out
