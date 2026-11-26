import os
import re
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

SERVER_ROOT = os.path.abspath(os.path.dirname(__file__))
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)


class TestServerOptimizations(unittest.TestCase):
    def test_reset_all_users_uses_update_many_and_regex_escaped(self):
        from Entities.Database.users_collection import UsersCollectionManager

        col = MagicMock()
        col.find.return_value.sort.return_value.limit.return_value = []
        mgr = UsersCollectionManager(col)

        mgr.reset_all_users_active_games()
        col.update_many.assert_called_once_with({}, {"$set": {"open_game_id": ""}})
        col.find_one_and_update.assert_not_called()

        self.assertIsNone(mgr.update_user("u1"))
        col.find_one_and_update.assert_not_called()

        mgr.search_users("test[1](2)")
        q_arg = col.find.call_args[0][0]
        self.assertEqual(q_arg["$or"][0]["_id"]["$regex"], re.escape("test[1](2)"))

    def test_user_game_histories_batches_round_queries(self):
        from Entities.Api_Services.user import user_game_histories

        mock_db = MagicMock()
        mock_db.game_play_history_manager.read_user_games_histories.return_value = [
            {
                "_id": "g1",
                "user1_id": "u1",
                "user2_id": "u2",
                "game_types": ["Chess"],
                "users_info": [
                    {"user_id": "u1", "username": "A", "image": 1},
                    {"user_id": "u2", "username": "B", "image": 2},
                ],
                "is_finished": True,
                "winner_id": "u1",
            },
            {
                "_id": "g2",
                "user1_id": "u1",
                "user2_id": "u2",
                "game_types": ["Ludo"],
                "users_info": [
                    {"user_id": "u1", "username": "A", "image": 1},
                    {"user_id": "u2", "username": "B", "image": 2},
                ],
                "is_finished": True,
                "winner_id": "u2",
            },
        ]
        mock_db.game_history_manager.read_rounds_by_game_play_ids.return_value = {
            "g1": [{"_id": "r1", "game_type": "Chess", "winner_id": 1, "winner_user_id": "u1", "date": datetime(2026, 1, 1)}],
            "g2": [],
        }

        with patch("Entities.Database.game_database", mock_db):
            res = user_game_histories("u1")

        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["my_result"], "win")
        self.assertEqual(res[1]["my_result"], "lose")
        mock_db.game_history_manager.read_rounds_by_game_play_ids.assert_called_once_with(["g1", "g2"])
        mock_db.game_history_manager.read_rounds_by_game_play_id.assert_not_called()

    def test_get_free_coin_atomic_and_none_last_chance(self):
        from fastapi import HTTPException
        from Entities.Api_Services.user import get_free_coin

        mock_db = MagicMock()
        mock_db.users_manager.collection.find_one_and_update.return_value = {"_id": "u1", "coin": 70}

        with patch("Entities.Database.game_database", mock_db):
            coin = get_free_coin("u1", 50, None)
        self.assertGreater(coin, 0)
        mock_db.users_manager.collection.find_one_and_update.assert_called_once()

        # Concurrent second call returns None -> 422
        mock_db.users_manager.collection.find_one_and_update.return_value = None
        with patch("Entities.Database.game_database", mock_db):
            with self.assertRaises(HTTPException):
                get_free_coin("u1", 50, datetime.now() - timedelta(hours=9))

    def test_purchase_replay_and_no_infinite_recursion(self):
        from Entities.Api_Services.user import purchase

        mock_db = MagicMock()
        mock_db.purchase_manager.has_purchase_token.return_value = True
        with patch("Entities.Database.game_database", mock_db):
            self.assertFalse(purchase("u1", "1", "Bazaar", "used_tok", 100))

        # Bazaar returns invalid JSON twice -> retries only once, no RecursionError
        mock_db.purchase_manager.has_purchase_token.return_value = False
        bad_resp = MagicMock()
        bad_resp.status_code = 500
        bad_resp.json.side_effect = ValueError("not json")
        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "new_tok"}

        with patch("Entities.Database.game_database", mock_db), \
             patch("Entities.Api_Services.user.requests.post", side_effect=[bad_resp, token_resp, bad_resp]) as mock_post:
            self.assertFalse(purchase("u1", "1", "Bazaar", "fresh_tok", 100))
            self.assertEqual(mock_post.call_count, 3)

    def test_sms_panel_attempt_limit_and_bot_bypass(self):
        from Entities.Security.sms_panel import SMSPanel

        panel = SMSPanel()
        with panel._lock:
            panel.numbers_to_codes["09120000001"] = ("5678", datetime.now(), 0)

        for _ in range(5):
            self.assertFalse(panel.check_code("09120000001", "0000"))
        # OTP is invalidated after 5 failed attempts, so even the right code fails now
        self.assertFalse(panel.check_code("09120000001", "5678"))
        # Bot phone master code still works
        self.assertTrue(panel.check_code("09131234567", "1234"))


if __name__ == "__main__":
    unittest.main()
