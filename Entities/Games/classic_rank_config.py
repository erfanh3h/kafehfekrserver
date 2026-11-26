"""
Classic Rank AI Difficulty & Reward Configuration for Cafe Fekr Server.
Mirrors kafehfekrbackend's authoritative Classic Rank reward & AI level definitions.
"""

from Entities.Games.game_types import GameTypesEnum

CLASSIC_RANK_DEFAULT_AI_LEVEL = 2
CLASSIC_RANK_AI_LEVELS = (1, 2, 3)

CLASSIC_RANK_LEVEL_METADATA = {
    1: {
        "level": 1,
        "key": "easy",
        "name_fa": "آسان",
        "name_en": "Easy",
        "subtitle_fa": "مناسب برای تمرین و گرم کردن",
    },
    2: {
        "level": 2,
        "key": "medium",
        "name_fa": "متوسط",
        "name_en": "Medium",
        "subtitle_fa": "رقابت متعادل و استاندارد (پیش‌فرض)",
    },
    3: {
        "level": 3,
        "key": "hard",
        "name_fa": "سخت",
        "name_en": "Hard",
        "subtitle_fa": "هوش مصنوعی حرفه‌ای با بیشترین پاداش",
    },
}

CLASSIC_RANK_REWARDS_TABLE = {
    "1": {
        "Easy": {"win_xp": 6, "draw_xp": 3, "lose_xp": 1, "win_coin": 2, "draw_coin": 0, "lose_coin": 0},
        "Normal": {"win_xp": 9, "draw_xp": 4, "lose_xp": 2, "win_coin": 2, "draw_coin": 1, "lose_coin": 0},
        "Hard": {"win_xp": 12, "draw_xp": 6, "lose_xp": 2, "win_coin": 3, "draw_coin": 1, "lose_coin": 0},
    },
    "2": {
        "Easy": {"win_xp": 10, "draw_xp": 5, "lose_xp": 2, "win_coin": 4, "draw_coin": 1, "lose_coin": 0},
        "Normal": {"win_xp": 15, "draw_xp": 7, "lose_xp": 3, "win_coin": 5, "draw_coin": 2, "lose_coin": 0},
        "Hard": {"win_xp": 22, "draw_xp": 11, "lose_xp": 5, "win_coin": 6, "draw_coin": 2, "lose_coin": 0},
    },
    "3": {
        "Easy": {"win_xp": 16, "draw_xp": 8, "lose_xp": 4, "win_coin": 7, "draw_coin": 3, "lose_coin": 0},
        "Normal": {"win_xp": 24, "draw_xp": 12, "lose_xp": 5, "win_coin": 9, "draw_coin": 4, "lose_coin": 0},
        "Hard": {"win_xp": 35, "draw_xp": 17, "lose_xp": 8, "win_coin": 12, "draw_coin": 5, "lose_coin": 0},
    },
}


def normalize_ai_level(level) -> int:
    """Normalizes AI opponent difficulty level to 1 (Easy), 2 (Medium, default), or 3 (Hard)."""
    if isinstance(level, bool):
        return CLASSIC_RANK_DEFAULT_AI_LEVEL
    if isinstance(level, (int, float)):
        lvl_int = int(level)
        return lvl_int if lvl_int in CLASSIC_RANK_AI_LEVELS else CLASSIC_RANK_DEFAULT_AI_LEVEL
    if isinstance(level, str):
        s = level.strip().lower()
        if s in ("1", "easy", "beginner", "lvl1", "level1"):
            return 1
        if s in ("2", "medium", "normal", "intermediate", "lvl2", "level2"):
            return 2
        if s in ("3", "hard", "master", "expert", "lvl3", "level3"):
            return 3
        try:
            lvl_int = int(s)
            return lvl_int if lvl_int in CLASSIC_RANK_AI_LEVELS else CLASSIC_RANK_DEFAULT_AI_LEVEL
        except ValueError:
            return CLASSIC_RANK_DEFAULT_AI_LEVEL
    return CLASSIC_RANK_DEFAULT_AI_LEVEL


def gametype_to_difficulty(game_type: str) -> str:
    val = game_type.value if hasattr(game_type, "value") else str(game_type or "")
    val_norm = val.lower().replace("_", "").replace("-", "")

    easy_types = (
        GameTypesEnum.TIC_TAC_TOE,
        GameTypesEnum.RPC,
        GameTypesEnum.DOTBOX,
        GameTypesEnum.LUDO,
        GameTypesEnum.MNUMBERS,
        GameTypesEnum.UNO,
    )
    for gt in easy_types:
        if val_norm == gt.value.lower().replace("_", "").replace("-", ""):
            return "Easy"

    hard_types = (
        GameTypesEnum.CHESS,
        GameTypesEnum.CHECKERS,
        GameTypesEnum.OTHELLO,
        GameTypesEnum.BACKGAMMON,
        GameTypesEnum.YINSH,
        GameTypesEnum.MILL,
        GameTypesEnum.RISK,
        GameTypesEnum.QUORIDOR,
    )
    for gt in hard_types:
        if val_norm == gt.value.lower().replace("_", "").replace("-", ""):
            return "Hard"

    return "Normal"


def get_classic_rank_reward_profile(game_type: str, ai_level=CLASSIC_RANK_DEFAULT_AI_LEVEL) -> dict:
    lvl = normalize_ai_level(ai_level)
    diff = gametype_to_difficulty(game_type)
    level_table = CLASSIC_RANK_REWARDS_TABLE.get(str(lvl), CLASSIC_RANK_REWARDS_TABLE[str(CLASSIC_RANK_DEFAULT_AI_LEVEL)])
    return dict(level_table.get(diff, level_table["Normal"]))


def get_classic_rank_config() -> dict:
    return {
        "default_ai_level": CLASSIC_RANK_DEFAULT_AI_LEVEL,
        "levels": [dict(CLASSIC_RANK_LEVEL_METADATA[lvl]) for lvl in CLASSIC_RANK_AI_LEVELS],
        "rewards": {k: {dk: dict(dv) for dk, dv in v.items()} for k, v in CLASSIC_RANK_REWARDS_TABLE.items()},
    }
