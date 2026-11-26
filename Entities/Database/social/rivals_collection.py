from datetime import datetime
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError


BOT_PREFIXES = ("bot_", "test_bot", "ai_")
BOT_EXACT_IDS = {"3gobru", "0", ""}


def is_bot_user_id(user_id) -> bool:
    if user_id is None:
        return True
    s = str(user_id).strip()
    low = s.lower()
    if low in BOT_EXACT_IDS:
        return True
    return any(low.startswith(pref) for pref in BOT_PREFIXES)


def make_pair_key(uid1: str, uid2: str) -> tuple[str, str, str]:
    a, b = sorted([str(uid1).strip(), str(uid2).strip()])
    return f"{a}__{b}", a, b


class RivalsCollectionManager:
    """Persistent head-to-head rivalry record between two human players."""

    ARCH_RIVAL_THRESHOLD = 5

    def __init__(self, collection):
        self.collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self):
        try:
            self.collection.create_index([("pair_key", ASCENDING)], unique=True)
            self.collection.create_index([("user_a", ASCENDING), ("last_played_at", DESCENDING)])
            self.collection.create_index([("user_b", ASCENDING), ("last_played_at", DESCENDING)])
        except Exception as e:
            print(f"[RivalsCollectionManager] Index setup warning: {e}")

    def _empty_summary(self, is_bot: bool = False) -> dict:
        return {
            "is_bot_match": bool(is_bot),
            "my_wins": 0,
            "opp_wins": 0,
            "draws": 0,
            "total_matches": 0,
            "is_arch_rival": False,
            "last_game_type": "",
        }

    def format_for_viewer(self, doc: dict | None, viewer_id: str) -> dict:
        if not doc:
            return self._empty_summary(is_bot=False)
        vid = str(viewer_id).strip()
        is_a = str(doc.get("user_a", "")) == vid
        wins_a = int(doc.get("wins_a", 0) or 0)
        wins_b = int(doc.get("wins_b", 0) or 0)
        draws = int(doc.get("draws", 0) or 0)
        total = int(doc.get("total_matches", wins_a + wins_b + draws) or 0)
        my_wins = wins_a if is_a else wins_b
        opp_wins = wins_b if is_a else wins_a
        return {
            "is_bot_match": False,
            "my_wins": my_wins,
            "opp_wins": opp_wins,
            "draws": draws,
            "total_matches": total,
            "is_arch_rival": total >= self.ARCH_RIVAL_THRESHOLD,
            "last_game_type": str(doc.get("last_game_type", "") or ""),
        }

    def record_match_result(
        self,
        uid1: str,
        uid2: str,
        winner_user_id,
        game_type: str = "",
        game_id: str = "",
        history_col=None,
    ) -> dict | None:
        u1 = str(uid1 or "").strip()
        u2 = str(uid2 or "").strip()
        if not u1 or not u2 or u1 == u2:
            return None
        if is_bot_user_id(u1) or is_bot_user_id(u2):
            return None

        pair_key, user_a, user_b = make_pair_key(u1, u2)
        clean_game_id = str(game_id or "").strip()
        clean_game_type = str(game_type or "").strip()

        # Backfill prior 2P history before creating a brand-new rivalry record
        if history_col is not None:
            existing = self.collection.find_one({"pair_key": pair_key}, {"_id": 1, "last_game_id": 1})
            if existing is None:
                self._backfill_from_history(
                    pair_key, user_a, user_b, history_col, exclude_game_id=clean_game_id
                )
            elif clean_game_id and str(existing.get("last_game_id", "")) == clean_game_id:
                return self.collection.find_one({"pair_key": pair_key})
        elif clean_game_id:
            existing = self.collection.find_one({"pair_key": pair_key}, {"last_game_id": 1})
            if existing and str(existing.get("last_game_id", "")) == clean_game_id:
                return self.collection.find_one({"pair_key": pair_key})

        w_str = str(winner_user_id).strip() if winner_user_id not in (None, 0, "0", "") else ""
        inc_fields = {"total_matches": 1}
        if w_str == user_a:
            inc_fields["wins_a"] = 1
        elif w_str == user_b:
            inc_fields["wins_b"] = 1
        else:
            inc_fields["draws"] = 1

        if clean_game_type:
            safe_gt = "".join(ch for ch in clean_game_type if ch.isalnum() or ch == "_")
            if safe_gt:
                if w_str == user_a:
                    inc_fields[f"per_game.{safe_gt}.wins_a"] = 1
                elif w_str == user_b:
                    inc_fields[f"per_game.{safe_gt}.wins_b"] = 1
                else:
                    inc_fields[f"per_game.{safe_gt}.draws"] = 1

        now = datetime.utcnow()
        set_fields = {
            "user_a": user_a,
            "user_b": user_b,
            "last_played_at": now,
        }
        if clean_game_type:
            set_fields["last_game_type"] = clean_game_type
        if clean_game_id:
            set_fields["last_game_id"] = clean_game_id

        query_filter = {"pair_key": pair_key}
        if clean_game_id:
            query_filter["last_game_id"] = {"$ne": clean_game_id}

        try:
            doc = self.collection.find_one_and_update(
                query_filter,
                {
                    "$inc": inc_fields,
                    "$set": set_fields,
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return doc
        except DuplicateKeyError:
            # Concurrent duplicate record for the same pair_key + last_game_id
            return self.collection.find_one({"pair_key": pair_key})

    def _extract_history_players(self, h: dict) -> list[str]:
        uids = h.get("user_ids")
        if isinstance(uids, list) and uids:
            return [str(u).strip() for u in uids if str(u).strip()]
        out = []
        for k in ("user1_id", "user2_id", "user3_id", "user4_id"):
            val = h.get(k)
            if val not in (None, ""):
                out.append(str(val).strip())
        if out:
            return out
        for k in ("player1", "player2"):
            val = h.get(k)
            if val not in (None, ""):
                out.append(str(val).strip())
        return out

    def _backfill_from_history(
        self,
        pair_key: str,
        user_a: str,
        user_b: str,
        history_col,
        exclude_game_id: str = "",
    ) -> dict | None:
        if history_col is None:
            return None
        try:
            query = {
                "game_score_type": {"$ne": "ClassicRank"},
                "$or": [
                    {"user_ids": {"$all": [user_a, user_b], "$size": 2}},
                    {"user1_id": user_a, "user2_id": user_b},
                    {"user1_id": user_b, "user2_id": user_a},
                    {"player1": user_a, "player2": user_b},
                    {"player1": user_b, "player2": user_a},
                ],
            }
            cursor = history_col.find(query).limit(250)
            wins_a = 0
            wins_b = 0
            draws = 0
            total = 0
            last_gt = ""
            last_dt = None
            excl = str(exclude_game_id or "").strip()

            for h in cursor:
                if excl and str(h.get("_id", "")).strip() == excl:
                    continue
                if str(h.get("game_score_type", "")).lower() == "classicrank":
                    continue
                # Must be strictly a 2-player match between user_a and user_b
                players = self._extract_history_players(h)
                if len(players) != 2 or set(players) != {user_a, user_b}:
                    continue

                is_fin = h.get("is_finished")
                w_id = h.get("winner_id")
                w_idx = h.get("winner")
                if is_fin is False:
                    continue
                if is_fin is None and w_id in (None, "") and (w_idx is None or w_idx == -1):
                    continue

                total += 1
                resolved_winner = ""
                if w_id not in (None, 0, "0", ""):
                    resolved_winner = str(w_id).strip()
                elif isinstance(h.get("user_scores"), list) and len(h["user_scores"]) >= 2:
                    s0 = int(h["user_scores"][0] or 0)
                    s1 = int(h["user_scores"][1] or 0)
                    if s0 > s1:
                        resolved_winner = players[0]
                    elif s1 > s0:
                        resolved_winner = players[1]
                elif w_idx in (1, 2):
                    resolved_winner = players[0] if w_idx == 1 else players[1]
                elif isinstance(h.get("winner_list"), list) and h["winner_list"]:
                    c1 = sum(1 for v in h["winner_list"] if v == 1)
                    c2 = sum(1 for v in h["winner_list"] if v == 2)
                    if c1 > c2:
                        resolved_winner = players[0]
                    elif c2 > c1:
                        resolved_winner = players[1]

                if resolved_winner == user_a:
                    wins_a += 1
                elif resolved_winner == user_b:
                    wins_b += 1
                else:
                    draws += 1

                gt_list = h.get("game_types")
                if isinstance(gt_list, list) and gt_list:
                    last_gt = str(gt_list[-1])
                elif h.get("current_game_type"):
                    last_gt = str(h.get("current_game_type"))
                elif h.get("game_type"):
                    last_gt = str(h.get("game_type"))

                dt_val = h.get("finish_date") or h.get("updated_at") or h.get("start_date") or h.get("date") or h.get("created_at")
                if isinstance(dt_val, datetime) and (last_dt is None or dt_val > last_dt):
                    last_dt = dt_val

            if total <= 0:
                return None

            now = datetime.utcnow()
            doc = {
                "pair_key": pair_key,
                "user_a": user_a,
                "user_b": user_b,
                "wins_a": wins_a,
                "wins_b": wins_b,
                "draws": draws,
                "total_matches": total,
                "last_game_type": last_gt,
                "last_played_at": last_dt or now,
                "created_at": now,
            }
            self.collection.update_one(
                {"pair_key": pair_key},
                {"$setOnInsert": doc},
                upsert=True,
            )
            return self.collection.find_one({"pair_key": pair_key})
        except Exception as e:
            print(f"[RivalsCollectionManager] Backfill warning: {e}")
            return None

    def get_head_to_head(self, viewer_id: str, opponent_id: str, history_col=None) -> dict:
        vid = str(viewer_id or "").strip()
        oid = str(opponent_id or "").strip()
        if not vid or not oid or vid == oid or is_bot_user_id(vid) or is_bot_user_id(oid):
            return self._empty_summary(is_bot=is_bot_user_id(oid) or is_bot_user_id(vid))
        pair_key, user_a, user_b = make_pair_key(vid, oid)
        doc = self.collection.find_one({"pair_key": pair_key})
        if not doc and history_col is not None:
            doc = self._backfill_from_history(pair_key, user_a, user_b, history_col)
        return self.format_for_viewer(doc, vid)
