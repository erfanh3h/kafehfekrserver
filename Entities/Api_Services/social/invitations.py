from Entities import Network_Exeptions
from Entities.Database import game_database
from Entities.Api_Services.social.security import check_rate_limit, serialize_dt


def _format_invitation(inv: dict) -> dict:
    return {
        "invite_id": str(inv["_id"]),
        "from_user_id": str(inv.get("from_user_id", "")),
        "from_username": str(inv.get("from_username", "بازیکن")),
        "from_image": int(inv.get("from_image", 0) or 0),
        "to_user_id": str(inv.get("to_user_id", "")),
        "invite_mode": str(inv.get("invite_mode", "lobby")),
        "game_type": str(inv.get("game_type", "Ludo")),
        "lobby_id": str(inv.get("lobby_id", "")),
        "lobby_password": str(inv.get("lobby_password", "")),
        "player_count": int(inv.get("player_count", 2) or 2),
        "clan_id": str(inv.get("clan_id", "")),
        "status": str(inv.get("status", "pending")),
        "created_at": serialize_dt(inv.get("created_at")),
        "expires_at": serialize_dt(inv.get("expires_at")),
    }


def send_game_invitation(
    sender_data: dict,
    to_user_id: str,
    game_type: str = "Ludo",
    invite_mode: str = "lobby",
    lobby_id: str = "",
    lobby_password: str = "",
    player_count: int = 2,
) -> dict:
    fid = str(sender_data["_id"])
    tid = str(to_user_id).strip()
    check_rate_limit(fid, "game_invite")
    if not tid or fid == tid:
        raise Network_Exeptions.raise422(details="مخاطب دعوت‌نامه معتبر نیست.")
    if game_database.friends_manager.is_blocked(fid, tid):
        raise Network_Exeptions.raise403(details="امکان دعوت این بازیکن وجود ندارد.")

    target_user = game_database.users_manager.read_user(tid)
    if not target_user:
        raise Network_Exeptions.raise404(details="بازیکن مورد نظر یافت نشد.")

    # Must be either friends or in the same clan
    are_friends = game_database.friends_manager.are_friends(fid, tid)
    my_mem = game_database.clans_manager.get_user_membership(fid)
    th_mem = game_database.clans_manager.get_user_membership(tid)
    same_clan = (
        my_mem is not None
        and th_mem is not None
        and str(my_mem.get("clan_id")) == str(th_mem.get("clan_id"))
    )
    if not are_friends and not same_clan:
        raise Network_Exeptions.raise403(details="فقط می‌توانید دوستان یا هم‌کلنی‌های خود را دعوت کنید.")

    # Check if target player is already in an active match
    open_gid = str(target_user.get("open_game_id", "") or "")
    target_pres = game_database.presence_manager.get_presence(tid)
    if open_gid or target_pres.get("status") == "in_game":
        raise Network_Exeptions.raise409(details="این بازیکن در حال حاضر مشغول یک مسابقه دیگر است.")

    inv_doc = game_database.invitations_manager.create_invitation(
        from_user_id=fid,
        from_username=str(sender_data.get("username", "بازیکن")),
        from_image=int(sender_data.get("image", 0) or 0),
        to_user_id=tid,
        invite_mode=invite_mode,
        game_type=game_type,
        lobby_id=lobby_id,
        lobby_password=lobby_password,
        player_count=player_count,
        clan_id=str(my_mem["clan_id"]) if same_clan else "",
    )
    game_database.notifications_manager.create_notification(
        user_id=tid,
        notif_type="game_invitation_received",
        title="🎮 دعوت به بازی",
        body=f"{sender_data.get('username', 'بازیکن')} شما را به بازی «{game_type}» دعوت کرد!",
        actor_id=fid,
        actor_name=str(sender_data.get("username", "بازیکن")),
        actor_image=int(sender_data.get("image", 0) or 0),
        payload=_format_invitation(inv_doc),
        category="game_invitations",
    )
    return _format_invitation(inv_doc)


def respond_game_invitation(user_data: dict, invite_id: str, action: str) -> dict:
    uid = str(user_data["_id"])
    inv = game_database.invitations_manager.read_invitation(invite_id)
    if not inv:
        raise Network_Exeptions.raise404(details="دعوت‌نامه بازی یافت نشد.")
    if str(inv.get("to_user_id")) != uid:
        raise Network_Exeptions.raise403(details="این دعوت‌نامه برای شما ارسال نشده است.")
    if inv.get("status") != "pending":
        raise Network_Exeptions.raise422(details="این دعوت‌نامه منقضی شده یا قبلاً پاسخ داده شده است.")

    act = str(action or "").lower()
    if act not in ("accept", "reject"):
        raise Network_Exeptions.raise422(details="پاسخ نامعتبر است.")

    new_st = "accepted" if act == "accept" else "rejected"
    game_database.invitations_manager.update_status(invite_id, new_st)
    inv["status"] = new_st
    return _format_invitation(inv)


def list_active_invitations(user_id: str) -> list[dict]:
    docs = game_database.invitations_manager.get_incoming_invitations(user_id)
    return [_format_invitation(d) for d in docs]
