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
