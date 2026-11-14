from Entities import Network_Exeptions
from Entities.Database import game_database
from Entities.Games.game_types import GameTypesEnum
from Entities.Api_Services.social.security import (
    calculate_player_level,
    calculate_competitive_tier,
    sanitize_public_user_summary,
    serialize_dt,
)


ACHIEVEMENT_CATALOG = [
    {"id": "first_win", "title": "اولین پیروزی", "icon": "🏆", "desc": "کسب اولین برد در کافه فکر"},
    {"id": "veteran_25", "title": "کهنه‌کار کافه", "icon": "⚔️", "desc": "انجام حداقل ۲۵ مسابقه"},
    {"id": "champion_50", "title": "قهرمان ۵۰ برد", "icon": "👑", "desc": "کسب ۵۰ پیروزی در بازی‌ها"},
    {"id": "high_roller", "title": "استاد استراتژی", "icon": "💎", "desc": "رسیدن به امتیاز ۶۰۰ یا بالاتر"},
    {"id": "social_star", "title": "ستاره اجتماعی", "icon": "🤝", "desc": "داشتن حداقل ۵ دوست در کافه فکر"},
    {"id": "clan_warrior", "title": "هم‌رزم کلن", "icon": "🛡️", "desc": "عضویت در یک کلن فعال"},
]


def _compute_game_stats_and_favorites(history_doc: dict | None) -> dict:
    h = history_doc or {}
    per_game: list[dict] = []
    total_wins = 0
    total_losses = 0
    total_draws = 0

    for gt in [g.value for g in GameTypesEnum]:
        k = gt.lower()
        w = int(h.get(f"{k}_win", 0) or 0)
        l = int(h.get(f"{k}_lose", 0) or 0)
        d = int(h.get(f"{k}_draw", 0) or 0)
        r1 = int(h.get(f"{k}_rank1", 0) or 0)
        r2 = int(h.get(f"{k}_rank2", 0) or 0)
        total = w + l + d
        total_wins += w
        total_losses += l
        total_draws += d
        if total > 0:
            win_rate = round((w / total) * 100.0, 1)
            per_game.append(
                {
                    "game_type": gt,
                    "wins": w,
                    "losses": l,
                    "draws": d,
                    "rank1": r1,
                    "rank2": r2,
                    "total_matches": total,
                    "win_rate": win_rate,
                }
            )

    # Also include mode totals if per-game keys were zero
    mode_wins = (
        int(h.get("win_rank", 0) or 0)
        + int(h.get("win_classic_rank", 0) or 0)
        + int(h.get("win_multi_rank", 0) or 0)
    )
    mode_losses = (
        int(h.get("lose_rank", 0) or 0)
        + int(h.get("lose_classic_rank", 0) or 0)
        + int(h.get("lose_multi_rank", 0) or 0)
    )
    mode_draws = (
        int(h.get("draw_rank", 0) or 0)
        + int(h.get("draw_classic_rank", 0) or 0)
        + int(h.get("draw_multi_rank", 0) or 0)
    )
    total_wins = max(total_wins, mode_wins)
    total_losses = max(total_losses, mode_losses)
    total_draws = max(total_draws, mode_draws)
    total_matches = total_wins + total_losses + total_draws
    overall_win_rate = round((total_wins / total_matches) * 100.0, 1) if total_matches > 0 else 0.0

    most_played = sorted(per_game, key=lambda x: x["total_matches"], reverse=True)[:3]
    favorite_games = sorted(per_game, key=lambda x: (x["wins"], x["win_rate"]), reverse=True)[:3]

    return {
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_draws": total_draws,
        "total_matches": total_matches,
        "win_rate": overall_win_rate,
        "most_played_games": most_played,
        "favorite_games": favorite_games,
        "per_game_stats": per_game,
    }


def get_public_profile(viewer_id: str, target_user_id: str) -> dict:
    vid, tid = str(viewer_id), str(target_user_id).strip()
    if not tid:
        tid = vid
    user_doc = game_database.users_manager.read_user(tid)
    if not user_doc:
        raise Network_Exeptions.raise404(details="پروفایل بازیکن پیدا نشد.")

    is_self = vid == tid
    if not is_self and game_database.friends_manager.is_blocked(vid, tid):
        raise Network_Exeptions.raise403(details="امکان مشاهده این پروفایل وجود ندارد.")

    pres = game_database.presence_manager.get_presence(tid)
    mem = game_database.clans_manager.get_user_membership(tid)
    clan_info = None
    if mem:
        c_doc = game_database.clans_manager.read_clan(str(mem["clan_id"]))
        if c_doc:
            clan_info = {
                "_id": str(c_doc["_id"]),
                "clan_id": str(c_doc["_id"]),
                "name": str(c_doc.get("name", "")),
                "tag": str(c_doc.get("tag", "")),
                "emblem_id": int(c_doc.get("emblem_id", 1) or 1),
                "clan_level": int(c_doc.get("clan_level", 1) or 1),
                "role": str(mem.get("role", "member")),
                "contribution_score": int(mem.get("contribution_score", 0) or 0),
            }

    base = sanitize_public_user_summary(user_doc, pres, clan_info)
    hist_doc = game_database.user_history_manager.read_user_history(tid) or {}
    stats = _compute_game_stats_and_favorites(hist_doc)

    friend_ids = game_database.friends_manager.get_friend_ids(tid)
    unlocked_achievements = []
    if stats["total_wins"] >= 1:
        unlocked_achievements.append(ACHIEVEMENT_CATALOG[0])
    if stats["total_matches"] >= 25:
        unlocked_achievements.append(ACHIEVEMENT_CATALOG[1])
    if stats["total_wins"] >= 50:
        unlocked_achievements.append(ACHIEVEMENT_CATALOG[2])
    if int(user_doc.get("score", 0) or 0) >= 600:
        unlocked_achievements.append(ACHIEVEMENT_CATALOG[3])
    if len(friend_ids) >= 5:
        unlocked_achievements.append(ACHIEVEMENT_CATALOG[4])
    if clan_info is not None:
        unlocked_achievements.append(ACHIEVEMENT_CATALOG[5])

    priv = user_doc.get("privacy") if isinstance(user_doc.get("privacy"), dict) else {}
    show_history = is_self or bool(priv.get("show_match_history", True))
    recent_matches = []
    if show_history:
        try:
            from Entities.Api_Services import user as user_service
            recent_matches = user_service.user_game_histories(tid)[:10]
        except Exception:
            recent_matches = []

    relationship = "self" if is_self else "none"
    if not is_self:
        if game_database.friends_manager.are_friends(vid, tid):
            relationship = "friend"
        else:
            req = game_database.friends_manager.get_pending_request_between(vid, tid)
            if req:
                relationship = "request_sent" if str(req.get("from_user_id")) == vid else "request_received"

    base.update(
        {
            "join_date": serialize_dt(user_doc.get("join_date")),
            "friends_count": len(friend_ids),
            "relationship": relationship,
            "stats": stats,
            "history": hist_doc,
            "recent_matches": recent_matches,
            "achievements": unlocked_achievements,
            "privacy": priv if is_self else {},
        }
    )
    if is_self:
        base["coin"] = int(user_doc.get("coin", 0) or 0)
    return base


def update_my_profile_customization(
    user_id: str,
    profile_frame: int | None = None,
    profile_title: str | None = None,
    profile_badge: str | None = None,
    status_message: str | None = None,
    privacy: dict | None = None,
) -> dict:
    uid = str(user_id)
    game_database.users_manager.update_social_customization(
        user_id=uid,
        profile_frame=profile_frame,
        profile_title=profile_title,
        profile_badge=profile_badge,
        status_message=status_message,
        privacy=privacy,
    )
    return get_public_profile(uid, uid)
