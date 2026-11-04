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
