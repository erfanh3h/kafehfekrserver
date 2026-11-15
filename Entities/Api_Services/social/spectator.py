"""
Live Spectator Discovery Service (`kafehfekrserver`)
Provides paginated discovery of active, spectatable matches (`GET /spectator/live-games`)
with filtering by game_type, player_id, clan_id, and visibility scope (`all`, `friends`, `clan`).
Strictly enforces:
- Hidden-information game exclusion (`PRIVATE_STATE_GAMES` are never listed)
- Bidirectional block list checks
- Participant privacy settings (`show_current_game` and `allow_spectators`: `everyone`, `friends`, `clan`, `none`)
- Sanitized public player summaries (never exposing tokens, device IDs, or private state)
"""

from datetime import datetime, timedelta
import pymongo
from Entities.Database import game_database
from Entities.Api_Services.social.security import (
    calculate_player_level,
    calculate_competitive_tier,
    serialize_dt,
)

SAFE_SPECTATOR_GAMES = {
    "ludo",
    "monopoly",
    "risk",
    "chess",
    "checkers",
    "backgammon",
    "othello",
    "fourinrow",
    "connect4",
    "mill",
    "pentago",
    "quoridor",
    "tictactoe",
    "xo",
    "xogame",
    "boxfour",
    "dotbox",
    "dotsandboxes",
    "yinsh",
    "yatzy",
}

PRIVATE_STATE_GAMES = {
    "battleship",
    "uno",
    "coup",
    "fekrbekr",
    "sudoku",
    "msweeper",
    "mnumbers",
    "quiz",
    "rpc",
}


def _normalize_game_type(game_type: str) -> str:
    return str(game_type or "").strip().lower().replace("_", "").replace("-", "")


def is_game_spectatable(game_type: str) -> bool:
    norm = _normalize_game_type(game_type)
    if not norm or norm in PRIVATE_STATE_GAMES:
        return False
    return norm in SAFE_SPECTATOR_GAMES


def list_live_spectatable_games(
    viewer_id: str,
    game_type: str = "",
    player_id: str = "",
    clan_id: str = "",
    visibility_filter: str = "all",
    page: int = 1,
    limit: int = 20,
    filter_mode: str = "",
    filter_scope: str = "",
) -> dict:
    vid = str(viewer_id or "").strip()
    req_game_norm = _normalize_game_type(game_type)
    req_player_id = str(player_id or "").strip()
    req_clan_id = str(clan_id or "").strip()
    scope = str(filter_mode or filter_scope or visibility_filter or "all").strip().lower()
    if scope in ("everyone", "public", ""):
        scope = "all"

    page_num = max(1, int(page or 1))
    page_size = max(1, min(int(limit or 20), 50))

    friend_ids = set(str(fid) for fid in (game_database.friends_manager.get_friend_ids(vid) or []))
    my_mem = game_database.clans_manager.get_user_membership(vid)
    my_clan_id = str(my_mem.get("clan_id", "")) if isinstance(my_mem, dict) else ""
    if scope == "clan" and not req_clan_id and my_clan_id:
        req_clan_id = my_clan_id

    col = getattr(game_database.game_play_history_manager, "collection", None)
    if col is None:
        col = game_database.base_db["game_play_history"]
    cursor = col.find({"is_finished": {"$ne": True}}).sort([("start_date", pymongo.DESCENDING)]).limit(200)

    now = datetime.utcnow()
    stale_cutoff = now - timedelta(hours=3)

    matched_games: list[dict] = []

    for doc in cursor:
        if not isinstance(doc, dict):
            continue
        gid = str(doc.get("_id", "")).strip()
        if not gid:
            continue

        if doc.get("is_finished") is True or doc.get("is_running") is False or doc.get("end_time") is not None:
            continue
        if doc.get("is_spectatable") is False:
            continue

        start_dt = doc.get("start_date") or doc.get("start_time")
        updated_dt = doc.get("updated_at") or start_dt
        if isinstance(updated_dt, datetime) and updated_dt < stale_cutoff:
            continue

        raw_uids = doc.get("user_ids") or doc.get("gamers") or []
        user_ids = [
            str(u.get("user_id", u.get("id", "")) if isinstance(u, dict) else u)
            for u in raw_uids
            if u
        ]
        if not user_ids:
            continue

        # Viewer should not see a match they are currently playing in as a spectator target
        if vid in user_ids:
            continue

        # Filter by specific player_id if requested
        if req_player_id and req_player_id not in user_ids:
            continue

        # Determine active game_type
        g_types = [str(gt) for gt in (doc.get("game_types") or doc.get("games") or []) if gt]
        cur_idx = int(doc.get("current_game_index", 0) or 0)
        active_gtype = str(doc.get("current_game_type") or "")
        if not active_gtype and g_types:
            active_gtype = g_types[cur_idx] if 0 <= cur_idx < len(g_types) else g_types[0]

        if not is_game_spectatable(active_gtype):
            continue

        if req_game_norm and _normalize_game_type(active_gtype) != req_game_norm:
            continue

        allow_spec = doc.get("allow_spectators", True)
        if allow_spec is False or str(allow_spec).lower() == "none":
            continue

        # Load participant profiles, check blocks, privacy, friendships, and clans
        users_info_list = doc.get("users_info") if isinstance(doc.get("users_info"), list) else []
        users_info_by_id = {
            str(item.get("user_id", "")): item
            for item in users_info_list
            if isinstance(item, dict) and item.get("user_id")
        }

        is_blocked_match = False
        has_friend = False
        has_clanmate = False
        matches_requested_clan = False
        any_human_still_in_match = bool(doc.get("is_running", True))
        allowed_by_privacy = True
        human_count = 0
        effective_visibility = str(doc.get("visibility", "everyone") or "everyone").lower()

        players_summary: list[dict] = []

        for idx, pid in enumerate(user_ids):
            is_bot = pid.startswith("bot_") or pid.startswith("test_bot")
            fallback_info = users_info_by_id.get(pid, {})

            if is_bot:
                b_score = int(fallback_info.get("score", 1000) or 1000)
                b_tier = calculate_competitive_tier(b_score)
                players_summary.append({
                    "user_id": pid,
                    "gamer_id": idx + 1,
                    "username": str(fallback_info.get("username") or f"ربات {idx + 1}"),
                    "image": int(fallback_info.get("image", 0) or 0),
                    "avatar": int(fallback_info.get("image", 0) or 0),
                    "profile_frame": 0,
                    "profile_title": "",
                    "score": b_score,
                    "level": 1,
                    "rank_title": str(b_tier.get("title", b_tier.get("title_fa", "")) if isinstance(b_tier, dict) else ""),
                    "clan": None,
                    "is_friend": False,
                    "is_clanmate": False,
                })
                continue

            human_count += 1
            if game_database.friends_manager.is_blocked(vid, pid):
                is_blocked_match = True
                break

            u_doc = game_database.users_manager.read_user(pid)
            if not isinstance(u_doc, dict):
                continue

            open_gid = str(u_doc.get("open_game_id", "") or "")
            if open_gid == gid:
                any_human_still_in_match = True

            is_fr = pid in friend_ids
            if is_fr:
                has_friend = True

            p_mem = game_database.clans_manager.get_user_membership(pid)
            p_clan_id = str(p_mem.get("clan_id", "")) if isinstance(p_mem, dict) else ""
            is_cm = bool(my_clan_id and p_clan_id and my_clan_id == p_clan_id)
            if is_cm:
                has_clanmate = True
            if req_clan_id and p_clan_id == req_clan_id:
                matches_requested_clan = True

            clan_summary = None
            if p_clan_id:
                c_doc = game_database.clans_manager.read_clan(p_clan_id)
                if isinstance(c_doc, dict):
                    clan_summary = {
                        "clan_id": p_clan_id,
                        "name": str(c_doc.get("name", "")),
                        "tag": str(c_doc.get("tag", "")),
                        "emblem_id": int(c_doc.get("emblem_id", 1) or 1),
                    }

            priv = u_doc.get("privacy") if isinstance(u_doc.get("privacy"), dict) else {}
            show_game = bool(priv.get("show_current_game", True))
            spec_pref = str(priv.get("allow_spectators", effective_visibility or "everyone")).lower()

            if not show_game or spec_pref == "none":
                allowed_by_privacy = False
            elif spec_pref == "friends":
                if not is_fr:
                    allowed_by_privacy = False
                effective_visibility = "friends"
            elif spec_pref == "clan":
                if not (is_cm or is_fr):
                    allowed_by_privacy = False
                if effective_visibility == "everyone":
                    effective_visibility = "clan"

            u_score = int(u_doc.get("score", fallback_info.get("score", 0)) or 0)
            u_xp = int(u_doc.get("xp", 0) or 0)
            lvl_info = calculate_player_level(u_xp)
            lvl_val = int(lvl_info.get("level", 1)) if isinstance(lvl_info, dict) else int(lvl_info or 1)
            tier_info = calculate_competitive_tier(u_score)
            tier_title = str(tier_info.get("title", tier_info.get("title_fa", "")) if isinstance(tier_info, dict) else "")

            players_summary.append({
                "user_id": pid,
                "gamer_id": idx + 1,
                "username": str(u_doc.get("username") or fallback_info.get("username") or "بازیکن"),
                "image": int(u_doc.get("image", fallback_info.get("image", 0)) or 0),
                "avatar": int(u_doc.get("image", fallback_info.get("image", 0)) or 0),
                "profile_frame": int(u_doc.get("profile_frame", 0) or 0),
                "profile_title": str(u_doc.get("profile_title", "") or ""),
                "score": u_score,
                "level": lvl_val,
                "rank_title": tier_title,
                "clan": clan_summary,
                "is_friend": is_fr,
                "is_clanmate": is_cm,
            })

        if is_blocked_match:
            continue

        if human_count > 0:
            if not any_human_still_in_match:
                continue
            if not allowed_by_privacy:
                continue

        if effective_visibility == "friends" and not has_friend:
            continue
        if effective_visibility == "clan" and not (has_clanmate or has_friend):
            continue

        if scope == "friends" and not has_friend:
            continue
        if scope == "clan" and not (has_clanmate or matches_requested_clan):
            continue
        if req_clan_id and not matches_requested_clan:
            continue

        spec_count = int(doc.get("spectator_count", 0) or 0)
        matched_games.append({
            "game_id": gid,
            "game_type": active_gtype,
            "game_types": g_types or [active_gtype],
            "current_game_index": cur_idx,
            "game_score_type": doc.get("game_score_type", 0),
            "players": players_summary,
            "status": "in_progress",
            "spectator_count": max(0, spec_count),
            "started_at": serialize_dt(start_dt),
            "visibility": effective_visibility,
            "has_friend": has_friend,
            "has_clanmate": has_clanmate,
        })

    # Sort matches: friends' games first, then clanmates' games, then highest spectator_count, then newest
    matched_games.sort(
        key=lambda g: (
            1 if g.get("has_friend") else 0,
            1 if g.get("has_clanmate") else 0,
            int(g.get("spectator_count", 0)),
            str(g.get("started_at", "")),
        ),
        reverse=True,
    )

    total = len(matched_games)
    offset = (page_num - 1) * page_size
    page_items = matched_games[offset : offset + page_size]

    return {
        "items": page_items,
        "games": page_items,
        "page": page_num,
        "limit": page_size,
        "total": total,
        "has_more": (offset + page_size) < total,
    }


def list_live_games(
    viewer_id: str,
    game_type: str | None = None,
    player_id: str | None = None,
    clan_id: str | None = None,
    visibility: str | None = None,
    filter_scope: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    eff = filter_scope or visibility or "all"
    return list_live_spectatable_games(
        viewer_id=viewer_id,
        game_type=str(game_type or ""),
        player_id=str(player_id or ""),
        clan_id=str(clan_id or ""),
        visibility_filter=str(eff),
        page=page,
        limit=limit,
    )


def get_live_game_summary(viewer_id: str, game_id: str) -> dict:
    from Entities import Network_Exeptions
    gid = str(game_id or "").strip()
    if not gid:
        raise Network_Exeptions.raise404(details="شناسه مسابقه نامعتبر است.")
    res = list_live_spectatable_games(viewer_id=viewer_id, page=1, limit=50)
    for item in res.get("items", []):
        if str(item.get("game_id", "")) == gid:
            return item
    raise Network_Exeptions.raise404(details="این مسابقه به پایان رسیده یا امکان تماشای آن وجود ندارد.")

