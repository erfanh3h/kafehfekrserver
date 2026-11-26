from Entities.Database import game_database
from Entities.Database.social.rivals_collection import is_bot_user_id


def resolve_friend_status(viewer_id: str, opponent_id: str) -> tuple[str, str]:
    """Returns (friend_status, incoming_request_id).
    friend_status is one of: 'friends', 'outgoing_pending', 'incoming_pending', 'blocked', 'none', 'self', 'bot'.
    """
    vid = str(viewer_id or "").strip()
    oid = str(opponent_id or "").strip()
    if not oid or is_bot_user_id(oid):
        return "bot", ""
    if vid == oid:
        return "self", ""

    fm = game_database.friends_manager
    if fm.is_blocked(vid, oid):
        return "blocked", ""
    if fm.are_friends(vid, oid):
        return "friends", ""

    req = fm.get_pending_request_between(vid, oid)
    if req:
        req_id = str(req.get("_id", ""))
        if str(req.get("from_user_id", "")) == vid:
            return "outgoing_pending", ""
        return "incoming_pending", req_id
    return "none", ""


def get_rivalry_summary(viewer_id: str, opponent_user_id: str) -> dict:
    vid = str(viewer_id or "").strip()
    oid = str(opponent_user_id or "").strip()[:64]

    if not oid or is_bot_user_id(oid) or vid == oid:
        return {
            "eligible": False,
            "is_bot": is_bot_user_id(oid),
            "opponent_user_id": oid,
            "opponent_username": "",
            "opponent_image": 0,
            "opponent_profile_frame": 1,
            "my_wins": 0,
            "opp_wins": 0,
            "draws": 0,
            "total_matches": 0,
            "is_arch_rival": False,
            "last_game_type": "",
            "friend_status": "bot" if is_bot_user_id(oid) else "self",
            "incoming_request_id": "",
            "can_add_friend": False,
        }

    opp_doc = game_database.users_manager.read_user(oid)
    if not opp_doc or bool(opp_doc.get("is_bot", False)):
        is_bot_flag = bool(opp_doc and opp_doc.get("is_bot", False))
        return {
            "eligible": False,
            "is_bot": is_bot_flag,
            "opponent_user_id": oid,
            "opponent_username": "",
            "opponent_image": 0,
            "opponent_profile_frame": 1,
            "my_wins": 0,
            "opp_wins": 0,
            "draws": 0,
            "total_matches": 0,
            "is_arch_rival": False,
            "last_game_type": "",
            "friend_status": "bot" if is_bot_flag else "unknown",
            "incoming_request_id": "",
            "can_add_friend": False,
        }

    h2h = game_database.rivals_manager.get_head_to_head(
        vid,
        oid,
        history_col=game_database.game_play_history_manager.collection,
    )
    friend_status, incoming_req_id = resolve_friend_status(vid, oid)
    can_add_friend = friend_status in ("none", "incoming_pending")

    return {
        "eligible": friend_status != "blocked",
        "is_bot": False,
        "opponent_user_id": oid,
        "opponent_username": str(opp_doc.get("username", "حریف") or "حریف"),
        "opponent_image": int(opp_doc.get("image", 0) or 0),
        "opponent_profile_frame": int(opp_doc.get("profile_frame", 1) or 1),
        "my_wins": int(h2h.get("my_wins", 0) or 0),
        "opp_wins": int(h2h.get("opp_wins", 0) or 0),
        "draws": int(h2h.get("draws", 0) or 0),
        "total_matches": int(h2h.get("total_matches", 0) or 0),
        "is_arch_rival": bool(h2h.get("is_arch_rival", False)),
        "last_game_type": str(h2h.get("last_game_type", "") or ""),
        "friend_status": friend_status,
        "incoming_request_id": incoming_req_id,
        "can_add_friend": can_add_friend,
    }
