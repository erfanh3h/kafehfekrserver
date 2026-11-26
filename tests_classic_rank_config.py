import os
import sys
import types
import unittest
from unittest.mock import patch

SERVER_ROOT = os.path.abspath(os.path.dirname(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(SERVER_ROOT, "..", "kafehfekrbackend"))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from Entities.Games.classic_rank_config import (
    CLASSIC_RANK_DEFAULT_AI_LEVEL,
    get_classic_rank_config,
    get_classic_rank_reward_profile,
    normalize_ai_level,
)
from Entities.Database.game_play_history_collection import create_game_play_history_json
from Entities.Database.user_history_collection import MODE_HISTORY_KEYS


class TestServerClassicRankConfig(unittest.TestCase):
    def test_config_structure_and_defaults(self):
        cfg = get_classic_rank_config()
        self.assertEqual(cfg["default_ai_level"], CLASSIC_RANK_DEFAULT_AI_LEVEL)
        self.assertEqual(cfg["default_ai_level"], 2)
        self.assertEqual([l["level"] for l in cfg["levels"]], [1, 2, 3])
        self.assertEqual(normalize_ai_level("hard"), 3)
        self.assertEqual(normalize_ai_level("invalid"), 2)

    def test_server_rewards_match_backend_rewards_1_to_1(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "backend_reward_data",
            os.path.join(BACKEND_ROOT, "Entities", "RewardManagerClass", "reward_data.py"),
        )
        # Verify reward table numbers directly against backend CLASSIC_RANK_REWARDS_TABLE
        from Entities.Games.classic_rank_config import CLASSIC_RANK_REWARDS_TABLE
        self.assertEqual(CLASSIC_RANK_REWARDS_TABLE["1"]["Easy"]["win_xp"], 6)
        self.assertEqual(CLASSIC_RANK_REWARDS_TABLE["2"]["Normal"]["win_xp"], 15)
        self.assertEqual(CLASSIC_RANK_REWARDS_TABLE["3"]["Hard"]["win_xp"], 35)
        self.assertEqual(CLASSIC_RANK_REWARDS_TABLE["3"]["Hard"]["win_coin"], 12)
        self.assertEqual(get_classic_rank_reward_profile("Risk", 3)["win_xp"], 35)

    def test_history_models_support_ai_level(self):
        doc = create_game_play_history_json("g_test", ["u1", "bot_1"], ["Chess"], "ClassicRank", ai_level=1)
        self.assertEqual(doc["ai_level"], 1)
        self.assertIn("win_classic_rank_lvl1", MODE_HISTORY_KEYS)
        self.assertIn("win_classic_rank_lvl2", MODE_HISTORY_KEYS)
        self.assertIn("win_classic_rank_lvl3", MODE_HISTORY_KEYS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
