import copy
import sys
import types
import unittest
from datetime import datetime, timedelta


def _match_condition(val, cond, doc=None, key=None):
    if isinstance(cond, dict):
        for op, op_val in cond.items():
            if op == "$in":
                if isinstance(val, list):
                    if not any(v in op_val for v in val):
                        return False
                elif val not in op_val:
                    return False
            elif op == "$nin":
                if isinstance(val, list):
                    if any(v in op_val for v in val):
                        return False
                elif val in op_val:
                    return False
            elif op == "$ne":
                if val == op_val:
                    return False
            elif op == "$gt":
                if val is None or not (val > op_val):
                    return False
            elif op == "$gte":
                if val is None or not (val >= op_val):
                    return False
            elif op == "$lt":
                if val is None or not (val < op_val):
                    return False
            elif op == "$lte":
                if val is None or not (val <= op_val):
                    return False
            elif op == "$regex":
                import re
                flags = re.IGNORECASE if cond.get("$options") == "i" else 0
                if not re.search(op_val, str(val or ""), flags):
                    return False
            elif op == "$options":
                continue
        return True
    if isinstance(val, list) and not isinstance(cond, list):
        return cond in val
    return val == cond


def _match_query(doc, query):
    if not query:
        return True
    for k, v in query.items():
        if k == "$or":
            if not any(_match_query(doc, sub) for sub in v):
                return False
        elif k == "$and":
            if not all(_match_query(doc, sub) for sub in v):
                return False
        else:
            if not _match_condition(doc.get(k), v, doc, k):
                return False
    return True


class InMemoryCursor:
    def __init__(self, docs):
        self._docs = [copy.deepcopy(d) for d in docs]

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self._docs.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=(d == -1))
        else:
            self._docs.sort(
                key=lambda x: (x.get(key_or_list) is None, x.get(key_or_list)),
                reverse=(direction == -1),
            )
        return self

    def skip(self, n):
        self._docs = self._docs[int(n):]
        return self

    def limit(self, n):
        self._docs = self._docs[:int(n)]
        return self

    def __iter__(self):
        return iter(self._docs)


class InMemoryCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []
        self.unique_indexes = []

    def create_index(self, keys, unique=False, **kwargs):
        if unique:
            if isinstance(keys, str):
                self.unique_indexes.append([keys])
            else:
                self.unique_indexes.append([k for k, _ in keys])

    def _check_unique(self, candidate, exclude_idx=None):
        from pymongo.errors import DuplicateKeyError
        for fields in self.unique_indexes:
            for i, existing in enumerate(self.docs):
                if exclude_idx is not None and i == exclude_idx:
                    continue
                if all(existing.get(f) == candidate.get(f) and candidate.get(f) is not None for f in fields):
                    raise DuplicateKeyError(f"Duplicate key on {fields}")

    def insert_one(self, doc):
        d = copy.deepcopy(doc)
        if "_id" not in d:
            d["_id"] = f"id_{len(self.docs) + 1}"
        self._check_unique(d)
        self.docs.append(d)
        return types.SimpleNamespace(inserted_id=d["_id"])

    def find_one(self, query=None, projection=None, sort=None):
        matches = [d for d in self.docs if _match_query(d, query or {})]
        if sort:
            c = InMemoryCursor(matches).sort(sort)
            matches = list(c)
        if not matches:
            return None
        res = copy.deepcopy(matches[0])
        if projection and projection.get("_id") == 0:
            res.pop("_id", None)
        return res

    def find(self, query=None, projection=None):
        matches = []
        for d in self.docs:
            if _match_query(d, query or {}):
                item = copy.deepcopy(d)
                if projection and projection.get("_id") == 0:
                    item.pop("_id", None)
                matches.append(item)
        return InMemoryCursor(matches)

    def count_documents(self, query=None):
        return sum(1 for d in self.docs if _match_query(d, query or {}))

    def _apply_update(self, doc, update):
        for op, payload in update.items():
            if op == "$set":
                for k, v in payload.items():
                    if "." in k:
                        parts = k.split(".", 1)
                        doc.setdefault(parts[0], {})[parts[1]] = copy.deepcopy(v)
                    else:
                        doc[k] = copy.deepcopy(v)
            elif op == "$inc":
                for k, v in payload.items():
                    if "." in k:
                        parts = k.split(".", 1)
                        sub = doc.setdefault(parts[0], {})
                        sub[parts[1]] = sub.get(parts[1], 0) + v
                    else:
                        doc[k] = doc.get(k, 0) + v
            elif op == "$addToSet":
                for k, v in payload.items():
                    arr = doc.setdefault(k, [])
                    if v not in arr:
                        arr.append(copy.deepcopy(v))
            elif op == "$pull":
                for k, v in payload.items():
                    arr = doc.setdefault(k, [])
                    if v in arr:
                        arr.remove(v)
            elif op == "$setOnInsert":
                pass

    def update_one(self, query, update, upsert=False):
        for idx, d in enumerate(self.docs):
            if _match_query(d, query):
                self._apply_update(d, update)
                return types.SimpleNamespace(modified_count=1, matched_count=1)
        if upsert:
            new_doc = {}
            for k, v in query.items():
                if not k.startswith("$") and not isinstance(v, dict):
                    new_doc[k] = copy.deepcopy(v)
            if "$setOnInsert" in update:
                for k, v in update["$setOnInsert"].items():
                    new_doc[k] = copy.deepcopy(v)
            self._apply_update(new_doc, update)
            self.insert_one(new_doc)
            return types.SimpleNamespace(modified_count=1, matched_count=1)
        return types.SimpleNamespace(modified_count=0, matched_count=0)

    def update_many(self, query, update):
        mod = 0
        for d in self.docs:
            if _match_query(d, query):
                self._apply_update(d, update)
                mod += 1
        return types.SimpleNamespace(modified_count=mod)

    def find_one_and_update(self, query, update, upsert=False, return_document=True, projection=None):
        for d in self.docs:
            if _match_query(d, query):
                self._apply_update(d, update)
                res = copy.deepcopy(d)
                if projection and projection.get("_id") == 0:
                    res.pop("_id", None)
                return res
        if upsert:
            self.update_one(query, update, upsert=True)
            return self.find_one(query, projection=projection)
        return None

    def delete_one(self, query):
        for idx, d in enumerate(self.docs):
            if _match_query(d, query):
                self.docs.pop(idx)
                return types.SimpleNamespace(deleted_count=1)
        return types.SimpleNamespace(deleted_count=0)

    def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _match_query(d, query)]
        return types.SimpleNamespace(deleted_count=before - len(self.docs))


class InMemoryDB:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = InMemoryCollection(name)
        return self.collections[name]


class InMemoryMongoClient:
    def __init__(self, *args, **kwargs):
        self._dbs = {}

    def __getitem__(self, db_name):
        if db_name not in self._dbs:
            self._dbs[db_name] = InMemoryDB()
        return self._dbs[db_name]


class FakeHTTPException(Exception):
    def __init__(self, status_code=400, detail=""):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


def _install_test_stubs():
    if "pymongo" not in sys.modules:
        pymongo_mod = types.ModuleType("pymongo")
        pymongo_mod.ASCENDING = 1
        pymongo_mod.DESCENDING = -1
        pymongo_mod.ReturnDocument = types.SimpleNamespace(AFTER=True, BEFORE=False)
        pymongo_mod.MongoClient = InMemoryMongoClient
        errors_mod = types.ModuleType("pymongo.errors")

        class DuplicateKeyError(Exception):
            pass

        errors_mod.DuplicateKeyError = DuplicateKeyError
        pymongo_mod.errors = errors_mod
        sys.modules["pymongo"] = pymongo_mod
        sys.modules["pymongo.errors"] = errors_mod

    if "dotenv" not in sys.modules:
        dotenv_mod = types.ModuleType("dotenv")
        dotenv_mod.load_dotenv = lambda *a, **kw: None
        sys.modules["dotenv"] = dotenv_mod

    if "fastapi" not in sys.modules:
        fa_mod = types.ModuleType("fastapi")
        fa_mod.Header = lambda default=None, **kw: default
        fa_mod.HTTPException = FakeHTTPException
        fa_mod.status = types.SimpleNamespace(
            HTTP_401_UNAUTHORIZED=401,
            HTTP_400_BAD_REQUEST=400,
            HTTP_403_FORBIDDEN=403,
            HTTP_404_NOT_FOUND=404,
            HTTP_409_CONFLICT=409,
            HTTP_422_UNPROCESSABLE_ENTITY=422,
        )
        fa_mod.APIRouter = lambda **kw: types.SimpleNamespace(
            get=lambda *a, **k: (lambda fn: fn),
            post=lambda *a, **k: (lambda fn: fn),
        )
        sys.modules["fastapi"] = fa_mod

    if "jwt" not in sys.modules:
        jwt_mod = types.ModuleType("jwt")
        jwt_mod.encode = lambda payload, key, algorithm="HS256": "stub_jwt_token"
        jwt_mod.decode = lambda token, key, algorithms=None: {"id": "stub_user", "device_id": "dev1"}
        sys.modules["jwt"] = jwt_mod

    if "pydantic" not in sys.modules:
        pyd_mod = types.ModuleType("pydantic")

        class BaseModel:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        pyd_mod.BaseModel = BaseModel
        sys.modules["pydantic"] = pyd_mod


_install_test_stubs()

from Entities.Database import game_database
from Entities.Api_Services.social.security import (
    sanitize_text,
    validate_safe_name,
    validate_clan_tag,
    check_rate_limit,
    reset_rate_limits,
)
from Entities.Api_Services.social.friends import (
    send_friend_request,
    respond_friend_request,
    get_friends_list,
    remove_friend,
)
from Entities.Api_Services.social.moderation import block_player, unblock_player
from Entities.Api_Services.social.clans import (
    create_clan,
    join_or_request_clan,
    change_member_role,
    transfer_clan_leadership,
    leave_clan,
    kick_clan_member,
    CLAN_CREATION_COIN_COST,
)
from Entities.Api_Services.social.messages import (
    send_direct_message,
    get_direct_messages_history,
    send_clan_chat_message,
    delete_clan_chat_message,
)
from Entities.Api_Services.social.notifications import (
    list_notifications,
    mark_all_notifications_read,
    update_notification_preferences,
)
from Entities.Api_Services.social.invitations import (
    send_game_invitation,
    respond_game_invitation,
)
from Entities.Api_Services.social.profiles import (
    get_public_profile,
    update_my_profile_customization,
)
from Entities.Api_Services.social.leaderboards import get_social_leaderboard


class CafeFekrSocialSystemTests(unittest.TestCase):
    def setUp(self):
        reset_rate_limits()
        # Reset all collections in game_database
        for col in game_database.base_db.collections.values():
            col.docs.clear()

        # Seed 4 test players
        self.u1 = {"_id": "u1", "username": "Erfan", "coin": 500, "score": 1200, "xp": 800, "image": 1}
        self.u2 = {"_id": "u2", "username": "Niloofar", "coin": 400, "score": 1100, "xp": 600, "image": 2}
        self.u3 = {"_id": "u3", "username": "Reza", "coin": 100, "score": 950, "xp": 400, "image": 3}
        self.u4 = {"_id": "u4", "username": "Sara", "coin": 300, "score": 700, "xp": 200, "image": 4}
        for u in (self.u1, self.u2, self.u3, self.u4):
            game_database.base_db['users'].insert_one(u)

    # 1. Security, Sanitization, Validation & Rate Limiting
    def test_01_security_and_rate_limiting(self):
        self.assertEqual(sanitize_text("  سلام\x00 دنیا  ", 50), "سلام دنیا")
        self.assertEqual(validate_clan_tag("fekr99"), "#FEKR99")
        self.assertEqual(validate_safe_name("قهرمانان کافه"), "قهرمانان کافه")

        for _ in range(3):
            check_rate_limit("u_test_rate", "clan_create")
        with self.assertRaises(FakeHTTPException):
            check_rate_limit("u_test_rate", "clan_create")

    # 2. Friend Requests, Acceptance, Duplicate & Self-Request Prevention
    def test_02_friend_requests_and_acceptance(self):
        # Self-request blocked
        with self.assertRaises(FakeHTTPException):
            send_friend_request("u1", "u1", "سلام")

        # Valid request u1 -> u2
        req_res = send_friend_request("u1", "u2", "بیا بازی کنیم!")
        req_id = req_res["request_id"]
        self.assertEqual(req_res["status"], "pending")

        # Duplicate request blocked
        with self.assertRaises(FakeHTTPException):
            send_friend_request("u1", "u2", "دوباره")

        # Unauthorized third user u3 cannot accept u2's incoming request
        with self.assertRaises(FakeHTTPException):
            respond_friend_request("u3", req_id, "accept")

        # u2 accepts request
        acc_res = respond_friend_request("u2", req_id, "accept")
        self.assertEqual(acc_res["status"], "accepted")
        self.assertTrue(game_database.friends_manager.are_friends("u1", "u2"))

        f_list = get_friends_list("u1")
        self.assertEqual(len(f_list), 1)
        self.assertEqual(f_list[0]["user_id"], "u2")

        # Already friends -> cannot send duplicate friend request
        with self.assertRaises(FakeHTTPException):
            send_friend_request("u1", "u2")

    # 3. Blocking Behavior
    def test_03_blocking_clears_friendship_and_prevents_requests_and_dms(self):
        req_res = send_friend_request("u1", "u2")
        respond_friend_request("u2", req_res["request_id"], "accept")
        self.assertTrue(game_database.friends_manager.are_friends("u1", "u2"))

        # u1 blocks u2
        block_player("u1", "u2", "مزاحمت")
        self.assertFalse(game_database.friends_manager.are_friends("u1", "u2"))
        self.assertTrue(game_database.friends_manager.is_blocked("u1", "u2"))

        # Blocked user cannot send friend request or DM
        with self.assertRaises(FakeHTTPException):
            send_friend_request("u2", "u1")
        with self.assertRaises(FakeHTTPException):
            send_direct_message(self.u2, "u1", "سلام")

        # Unblock restores ability to interact
        unblock_player("u1", "u2")
        self.assertFalse(game_database.friends_manager.is_blocked("u1", "u2"))

    # 4. Clan Creation, Coin Cost Validation, Roles, Capacity & Leadership Transfer
    def test_04_clan_creation_roles_capacity_and_leadership_transfer(self):
        # u3 has only 100 coins (< 250 required) -> fails
        with self.assertRaises(FakeHTTPException):
            create_clan(self.u3, name="PoorClan", tag="#POOR")

        # u1 has 500 coins -> creates clan and deducts 250 coins
        u1_doc = game_database.users_manager.read_user("u1")
        clan = create_clan(
            u1_doc,
            name="اسطوره‌های کافه",
            tag="CAFE1",
            description="بهترین کلن کافه فکر",
            emblem_id=3,
            join_type="open",
            min_score=500,
        )
        clan_id = clan["clan_id"]
        self.assertEqual(clan["tag"], "#CAFE1")
        u1_after = game_database.users_manager.read_user("u1")
        self.assertEqual(u1_after["coin"], 500 - CLAN_CREATION_COIN_COST)

        # Duplicate clan tag or name prevented
        u2_doc = game_database.users_manager.read_user("u2")
        with self.assertRaises(FakeHTTPException):
            create_clan(u2_doc, name="اسطوره‌های کافه", tag="#OTHER")

        # u2 and u3 join open clan
        join_or_request_clan(u2_doc, clan_id)
        u3_doc = game_database.users_manager.read_user("u3")
        join_or_request_clan(u3_doc, clan_id)

        # Promote u2 to elder, then co_leader
        change_member_role(u1_after, "u2", "elder")
        self.assertEqual(game_database.clans_manager.get_user_membership("u2")["role"], "elder")

        # Elder u2 cannot promote u3 to co_leader (insufficient role)
        with self.assertRaises(FakeHTTPException):
            change_member_role(u2_doc, "u3", "co_leader")

        # Leader u1 cannot leave without transferring leadership first
        with self.assertRaises(FakeHTTPException):
            leave_clan(u1_after)

        # Transfer leadership from u1 to u2
        transfer_clan_leadership(u1_after, "u2")
        self.assertEqual(game_database.clans_manager.read_clan(clan_id)["leader_id"], "u2")
        self.assertEqual(game_database.clans_manager.get_user_membership("u1")["role"], "co_leader")

        # Atomic capacity check
        game_database.clans_manager.clans.update_one({"_id": clan_id}, {"$set": {"max_members": 3}})
        ok_cap, reason = game_database.clans_manager.add_member_atomic(clan_id, "u4")
        self.assertFalse(ok_cap)
        self.assertEqual(reason, "clan_full")

    # 5. Clan Competitive Progression & Anti-Farming Protection
    def test_05_clan_contribution_and_anti_farming(self):
        u1_doc = game_database.users_manager.read_user("u1")
        clan = create_clan(u1_doc, name="Warriors", tag="#WARR")
        clan_id = clan["clan_id"]
        u2_doc = game_database.users_manager.read_user("u2")
        join_or_request_clan(u2_doc, clan_id)

        # Ranked win against external player u3 awards clan score & XP (up to 3 matches within 2h)
        for _ in range(3):
            res1 = game_database.clans_manager.record_member_match_contribution(
                user_id="u1", is_win=True, xp_earned=50, score_earned=25, opponent_ids=["u3"], is_ranked=True
            )
            self.assertFalse(res1["is_farmed"])
            self.assertGreater(res1["contrib_pts"], 0)

        # 4th match against same opponent u3 within 2 hours is blocked by anti-farming cooldown
        res_repeat = game_database.clans_manager.record_member_match_contribution(
            user_id="u1", is_win=True, xp_earned=50, score_earned=25, opponent_ids=["u3"], is_ranked=True
        )
        self.assertTrue(res_repeat["is_farmed"])
        self.assertEqual(res_repeat["contrib_pts"], 0)

        # Match against own clanmate u2 is blocked from clan score farming
        res_internal = game_database.clans_manager.record_member_match_contribution(
            user_id="u1", is_win=True, xp_earned=50, score_earned=25, opponent_ids=["u2"], is_ranked=True
        )
        self.assertTrue(res_internal["is_farmed"])
        self.assertEqual(res_internal["contrib_pts"], 0)

    # 6. Clan Chat & Moderator Message Deletion
    def test_06_clan_chat_and_moderator_deletion(self):
        u1_doc = game_database.users_manager.read_user("u1")
        clan = create_clan(u1_doc, name="Chatters", tag="#CHAT")
        u2_doc = game_database.users_manager.read_user("u2")
        u3_doc = game_database.users_manager.read_user("u3")
        join_or_request_clan(u2_doc, clan["clan_id"])
        join_or_request_clan(u3_doc, clan["clan_id"])

        msg = send_clan_chat_message(u2_doc, "سلام @Erfan خوبی؟")
        self.assertIn("Erfan", msg["mentions"])

        # Regular member u3 cannot delete u2's message
        with self.assertRaises(FakeHTTPException):
            delete_clan_chat_message(u3_doc, msg["message_id"])

        # Leader u1 can delete u2's message
        del_res = delete_clan_chat_message(u1_doc, msg["message_id"])
        self.assertTrue(del_res["deleted"])

    # 7. Direct Messaging, Privacy & Read Receipts
    def test_07_direct_messages_privacy_and_read_receipts(self):
        # Configure u4 privacy to allow DMs from friends only
        update_my_profile_customization("u4", privacy={"allow_dms": "friends"})
        with self.assertRaises(FakeHTTPException):
            send_direct_message(self.u1, "u4", "سلام سارا")

        # Send DM between u1 and u2
        dm = send_direct_message(self.u1, "u2", "سلام نیلوفر! نوبت توست")
        self.assertEqual(dm["text"], "سلام نیلوفر! نوبت توست")
        self.assertEqual(game_database.direct_messages_manager.get_total_unread_count("u2"), 1)

        # Reading history marks messages read
        hist = get_direct_messages_history("u2", "u1")
        self.assertEqual(len(hist["messages"]), 1)
        self.assertEqual(game_database.direct_messages_manager.get_total_unread_count("u2"), 0)

    # 8. Notifications & Preferences
    def test_08_notifications_and_preferences(self):
        update_notification_preferences("u2", {"game_invitations": False})
        skipped = game_database.notifications_manager.create_notification(
            user_id="u2", notif_type="game_invite", title="دعوت بازی", body="تست"
        )
        self.assertIsNone(skipped)

        created = game_database.notifications_manager.create_notification(
            user_id="u2", notif_type="friend_request", title="درخواست دوستی", body="عرفان درخواست داد"
        )
        self.assertIsNotNone(created)
        listing = list_notifications("u2", unread_only=True)
        self.assertEqual(listing["unread_count"], 1)

        mark_all_notifications_read("u2")
        self.assertEqual(list_notifications("u2", unread_only=True)["unread_count"], 0)

    # 9. Multi-Socket Presence & Reconnect Behavior
    def test_09_multi_socket_presence_reconnect(self):
        game_database.presence_manager.update_presence(
            "u1", "online", socket_id="sid_a", add_socket=True
        )
        game_database.presence_manager.update_presence(
            "u1", "in_game", current_game_type="Monopoly", current_game_id="g_99", socket_id="sid_b", add_socket=True
        )
        p1 = game_database.presence_manager.get_presence("u1")
        self.assertEqual(p1["status"], "in_game")
        self.assertEqual(p1["current_game_id"], "g_99")

        # Disconnect sid_a while sid_b is still connected -> remains online/in_game
        game_database.presence_manager.update_presence(
            "u1", "offline", socket_id="sid_a", add_socket=False
        )
        p2 = game_database.presence_manager.get_presence("u1")
        self.assertNotEqual(p2["status"], "offline")

        # Disconnect sid_b -> now transitions to offline
        game_database.presence_manager.update_presence(
            "u1", "offline", socket_id="sid_b", add_socket=False
        )
        p3 = game_database.presence_manager.get_presence("u1")
        self.assertEqual(p3["status"], "offline")

    # 10. Game Invitations, Profile Privacy & Social Leaderboards
    def test_10_invitations_profiles_and_leaderboards(self):
        # Make u1 and u2 friends
        req = send_friend_request("u1", "u2")
        respond_friend_request("u2", req["request_id"], "accept")

        u1_doc = game_database.users_manager.read_user("u1")
        u2_doc = game_database.users_manager.read_user("u2")
        inv = send_game_invitation(u1_doc, "u2", invite_mode="direct_match", game_type="Monopoly")
        self.assertEqual(inv["game_type"], "Monopoly")

        # Duplicate active invite returns existing pending invitation idempotently without creating duplicates
        inv_dup = send_game_invitation(u1_doc, "u2", invite_mode="direct_match", game_type="Monopoly")
        self.assertEqual(inv_dup["invite_id"], inv["invite_id"])

        # Accept invitation
        acc = respond_game_invitation(u2_doc, inv["invite_id"], "accept")
        self.assertEqual(acc["status"], "accepted")

        # Public profile & leaderboards
        prof = get_public_profile("u1", "u2")
        self.assertEqual(prof["username"], "Niloofar")
        self.assertEqual(prof["relationship"], "friend")

        lb_friends = get_social_leaderboard("u1", board_type="friends")
        self.assertEqual(len(lb_friends), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
