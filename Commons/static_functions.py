import string, random


def make_command_json(id, data=None):
    return {'id': id, 'data': data}


def create_random_name() -> str:
    char_set = string.ascii_uppercase + string.digits
    random_name = ''.join(random.sample(char_set * 6, 6))
    return random_name


def create_random_game_id() -> str:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, 7))
    return result


def create_random_user_id(length=6) -> str:
    char_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    result = ''.join(random.sample(char_set * 6, length))
    return result


def create_random_code() -> str:
    char_set = string.digits
    result = ''.join(random.sample(char_set * 6, 4))
    return result


def get_random_coin() -> int:
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    number = random.choice(numbers)
    if number == 1 or number == 9:
        return 4
    if number == 2 or number == 8:
        return 8
    if number == 3 or number == 7:
        return 12
    if number == 4 or number == 6:
        return 16
    if number == 5:
        return 20
    return 0


PERSIAN_ARABIC_DIGITS = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
}


def clean_phone_number(raw_phone: str) -> str:
    if not raw_phone:
        return ""
    s = "".join(PERSIAN_ARABIC_DIGITS.get(ch, ch) for ch in str(raw_phone).strip())
    s = "".join(ch for ch in s if ch.isdigit() or ch == '+')
    if s.startswith("+98"):
        s = "0" + s[3:]
    elif s.startswith("0098"):
        s = "0" + s[4:]
    elif s.startswith("98") and len(s) == 12:
        s = "0" + s[2:]
    elif s.startswith("9") and len(s) == 10:
        s = "0" + s
    return s


def clean_code(raw_code: str) -> str:
    if not raw_code:
        return ""
    s = "".join(PERSIAN_ARABIC_DIGITS.get(ch, ch) for ch in str(raw_code).strip())
    return "".join(ch for ch in s if ch.isdigit())


KNOWN_BOT_PHONES = {
    "09131234567",
    "9131234567",
    "09000000000",
    "09999999999",
}


def is_bot_phone(phone: str) -> bool:
    if not phone:
        return False
    clean = clean_phone_number(phone)
    if not clean:
        return False
    if (
        clean in KNOWN_BOT_PHONES
        or clean.startswith("bot_")
        or clean.startswith("test_bot")
        or clean.endswith("1234567")
        or (len(clean) == 11 and len(set(clean[2:])) <= 1)
    ):
        return True
    try:
        from Entities.Database import game_database
        user = game_database.users_manager.read_user_by_phone(clean)
        if user:
            if user.get('_id') == '3goBRU':
                return True
            if str(user.get('device_id', '')).startswith('bot_'):
                return True
            if user.get('is_bot') is True:
                return True
    except Exception:
        pass
    return False


def parse_version(ver_str: str) -> tuple:
    """Parses a version string like '2.0.1' into a tuple of ints (2, 0, 1)."""
    try:
        parts = []
        for segment in str(ver_str or "").strip().split("."):
            digits = "".join(ch for ch in segment if ch.isdigit())
            parts.append(int(digits) if digits else 0)
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def is_version_allowed(current_ver: str, allowed_ver: str) -> bool:
    """Returns True if current_ver is greater than or equal to allowed_ver."""
    if not allowed_ver or not str(allowed_ver).strip():
        return True
    return parse_version(current_ver) >= parse_version(allowed_ver)


def _parse_utc_datetime(val):
    """Parses a datetime or ISO string into a timezone-aware UTC datetime, or None."""
    from datetime import datetime, timezone
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def is_ban_expired(user_data: dict | None) -> bool:
    """Returns True if the user has a temporary ban whose ban_until timestamp is in the past."""
    if not user_data or not isinstance(user_data, dict):
        return False
    ban_until = _parse_utc_datetime(user_data.get("ban_until"))
    if ban_until is None:
        return False
    from datetime import datetime, timezone
    return datetime.now(timezone.utc) >= ban_until


def is_user_banned(user_data: dict | None) -> bool:
    """Returns True if the user account is inactive or flagged as banned (respecting ban_until expiry)."""
    if not user_data or not isinstance(user_data, dict):
        return False
    flagged = (user_data.get("is_active") is False) or (user_data.get("is_banned") is True)
    if not flagged:
        return False
    if is_ban_expired(user_data):
        return False
    return True


def check_ban_and_auto_unban(user_data: dict | None, users_manager=None) -> bool:
    """Checks ban status and auto-clears expired temporary bans in MongoDB when encountered."""
    if not user_data or not isinstance(user_data, dict):
        return False
    flagged = (user_data.get("is_active") is False) or (user_data.get("is_banned") is True)
    if not flagged:
        return False
    if is_ban_expired(user_data):
        uid = user_data.get("_id")
        if uid and users_manager is not None and hasattr(users_manager, "collection"):
            try:
                users_manager.collection.update_one(
                    {"_id": uid},
                    {
                        "$set": {"is_active": True, "is_banned": False},
                        "$unset": {"ban_until": "", "ban_reason": "", "banned_at": ""},
                    },
                )
            except Exception as e:
                print(f"[auto_unban] Failed to clear expired ban for {uid}: {e}")
        user_data["is_active"] = True
        user_data["is_banned"] = False
        user_data.pop("ban_until", None)
        return False
    return True


def get_maintenance_block(config_data: dict | None) -> str | None:
    """Returns maintenance message if maintenance mode is active, otherwise None."""
    if not isinstance(config_data, dict):
        return None
    if bool(config_data.get("maintenance_mode", False)):
        msg = str(config_data.get("maintenance_message") or "").strip()
        return msg or "سرور در حال به‌روزرسانی و تعمیرات است. لطفاً دقایقی دیگر تلاش کنید."
    return None
