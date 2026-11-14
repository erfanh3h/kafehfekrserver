from datetime import datetime, timedelta
import pymongo
from Commons.static_functions import create_random_name


CLAN_ROLE_RANK = {
    "member": 1,
    "elder": 2,
    "co_leader": 3,
    "leader": 4,
}

CLAN_ROLE_FA = {
    "leader": "رهبر کلن",
    "co_leader": "قائم‌مقام",
    "elder": "ارشد",
    "member": "عضو",
}

DEFAULT_MAX_CLAN_MEMBERS = 40
CLAN_CREATION_COIN_COST = 250


def calculate_clan_level(clan_xp: int) -> int:
    if clan_xp <= 0:
        return 1
    # Progressive clan level curve: Level 1: 0 XP, Level 2: 200 XP, Level 3: 600 XP, Level 4: 1200 XP...
    lvl = 1
    while 100 * lvl * (lvl - 1) <= clan_xp and lvl < 50:
        if 100 * (lvl + 1) * lvl <= clan_xp:
            lvl += 1
        else:
            break
    return max(1, lvl)


class ClansCollectionManager:
    """Manages clans, clan_members, clan_join_requests, clan_invitations, clan_challenges, and clan_audit_logs."""

    def __init__(
        self,
        clans_col,
        members_col,
        join_requests_col,
        invitations_col,
        challenges_col,
        audit_logs_col,
    ):
        self.clans = clans_col
        self.members = members_col
        self.join_requests = join_requests_col
        self.invitations = invitations_col
        self.challenges = challenges_col
        self.audit_logs = audit_logs_col
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.clans.create_index([("name_lower", pymongo.ASCENDING)], unique=True)
            self.clans.create_index([("tag_upper", pymongo.ASCENDING)], unique=True)
            self.clans.create_index([("clan_score", pymongo.DESCENDING)])
            self.clans.create_index([("weekly_score", pymongo.DESCENDING)])
            self.clans.create_index([("monthly_score", pymongo.DESCENDING)])
            self.members.create_index([("user_id", pymongo.ASCENDING)], unique=True)
            self.members.create_index([("clan_id", pymongo.ASCENDING), ("contribution_score", pymongo.DESCENDING)])
            self.join_requests.create_index(
                [("clan_id", pymongo.ASCENDING), ("user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]
            )
            self.invitations.create_index(
                [("clan_id", pymongo.ASCENDING), ("to_user_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]
            )
            self.challenges.create_index([("clan_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)])
            self.audit_logs.create_index([("clan_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
        except Exception:
            pass

    def log_audit(self, clan_id: str, actor_id: str, action: str, target_id: str = "", details: dict | None = None):
        doc = {
            "_id": f"caud_{create_random_name()}",
            "clan_id": str(clan_id),
            "actor_id": str(actor_id),
            "action": str(action),
            "target_id": str(target_id or ""),
            "details": details or {},
            "created_at": datetime.now(),
        }
        try:
            self.audit_logs.insert_one(doc)
        except Exception:
            pass
        return doc

    def get_audit_logs(self, clan_id: str, limit: int = 40) -> list[dict]:
        cursor = (
            self.audit_logs.find({"clan_id": str(clan_id)})
            .sort("created_at", -1)
            .limit(max(1, min(limit, 100)))
        )
        return list(cursor)

    # --- Clan Lookup ---
    def read_clan(self, clan_id: str):
        return self.clans.find_one({"_id": str(clan_id)})

    def read_clan_by_tag(self, tag: str):
        t = str(tag or "").strip().upper()
        if not t.startswith("#"):
            t = "#" + t
        return self.clans.find_one({"tag_upper": t})

    def read_clan_by_name(self, name: str):
        return self.clans.find_one({"name_lower": str(name or "").strip().lower()})

    def get_user_membership(self, user_id: str):
        return self.members.find_one({"user_id": str(user_id)})

    def get_clan_members(self, clan_id: str) -> list[dict]:
        cursor = self.members.find({"clan_id": str(clan_id)}).sort(
            [("role_rank", pymongo.DESCENDING), ("contribution_score", pymongo.DESCENDING)]
        )
        return list(cursor)

    # --- Clan Creation & Directory ---
    def create_clan(
        self,
        leader_id: str,
        name: str,
        tag: str,
        emblem_id: int = 1,
        description: str = "",
        language: str = "fa",
        join_type: str = "open",
        min_score: int = 0,
        min_level: int = 1,
        max_members: int = DEFAULT_MAX_CLAN_MEMBERS,
    ) -> dict:
        clean_name = str(name).strip()
        clean_tag = str(tag).strip().upper()
        if not clean_tag.startswith("#"):
            clean_tag = "#" + clean_tag
        if join_type not in ("open", "request", "invite_only"):
            join_type = "open"
        now = datetime.now()
        clan_id = f"clan_{create_random_name()}"
        clan_doc = {
            "_id": clan_id,
            "name": clean_name,
            "name_lower": clean_name.lower(),
            "tag": clean_tag,
            "tag_upper": clean_tag.upper(),
            "emblem_id": max(0, int(emblem_id)),
            "description": str(description or "").strip()[:300],
            "language": str(language or "fa")[:10],
            "join_type": join_type,
            "min_score": max(0, int(min_score)),
            "min_level": max(1, int(min_level)),
            "leader_id": str(leader_id),
            "clan_level": 1,
            "clan_xp": 0,
            "member_count": 1,
            "max_members": max(5, min(int(max_members), 50)),
            "clan_score": 0,
            "weekly_score": 0,
            "monthly_score": 0,
            "total_wins": 0,
            "total_matches": 0,
            "achievements": [],
            "week_key": now.strftime("%Y-W%W"),
            "month_key": now.strftime("%Y-%m"),
            "created_at": now,
            "updated_at": now,
        }
        self.clans.insert_one(clan_doc)

        member_doc = {
            "_id": f"cmem_{clan_id}_{leader_id}",
            "clan_id": clan_id,
            "user_id": str(leader_id),
            "role": "leader",
            "role_rank": CLAN_ROLE_RANK["leader"],
            "contribution_score": 0,
            "weekly_contribution": 0,
            "monthly_contribution": 0,
            "contribution_xp": 0,
            "matches_played": 0,
            "matches_won": 0,
            "recent_opponents": {},
            "joined_at": now,
            "last_active_at": now,
        }
        self.members.insert_one(member_doc)
        self.log_audit(clan_id, leader_id, "clan_created", leader_id, {"name": clean_name, "tag": clean_tag})
        return clan_doc

    def search_clans(
        self,
        query_text: str = "",
        join_type: str = "",
        language: str = "",
        min_members: int = 0,
        only_joinable: bool = False,
        sort_by: str = "clan_score",
        skip: int = 0,
        limit: int = 30,
    ) -> list[dict]:
        q: dict = {}
        qt = str(query_text or "").strip()
        if qt:
            if qt.startswith("#"):
                q["tag_upper"] = {"$regex": qt.upper()}
            else:
                q["$or"] = [
                    {"name_lower": {"$regex": qt.lower()}},
                    {"tag_upper": {"$regex": qt.upper()}},
                ]
        if join_type in ("open", "request", "invite_only"):
            q["join_type"] = join_type
        if language:
            q["language"] = str(language)
        if min_members > 0:
            q["member_count"] = {"$gte": int(min_members)}
        if only_joinable:
            q["member_count"] = {"$lt": DEFAULT_MAX_CLAN_MEMBERS}
            if "join_type" not in q:
                q["join_type"] = {"$in": ["open", "request"]}

        sort_field = "clan_score"
        if sort_by in ("clan_score", "weekly_score", "monthly_score", "clan_xp", "member_count", "created_at"):
            sort_field = sort_by
        cursor = (
            self.clans.find(q)
            .sort([(sort_field, pymongo.DESCENDING)])
            .skip(max(0, int(skip)))
            .limit(max(1, min(int(limit), 50)))
        )
        return list(cursor)

    def update_clan_settings(self, clan_id: str, updates: dict):
        allowed = {}
        if "description" in updates and updates["description"] is not None:
            allowed["description"] = str(updates["description"]).strip()[:300]
        if "emblem_id" in updates and updates["emblem_id"] is not None:
            allowed["emblem_id"] = max(0, int(updates["emblem_id"]))
        if "language" in updates and updates["language"] is not None:
            allowed["language"] = str(updates["language"]).strip()[:10]
        if "join_type" in updates and updates["join_type"] in ("open", "request", "invite_only"):
            allowed["join_type"] = updates["join_type"]
        if "min_score" in updates and updates["min_score"] is not None:
            allowed["min_score"] = max(0, int(updates["min_score"]))
        if "min_level" in updates and updates["min_level"] is not None:
            allowed["min_level"] = max(1, int(updates["min_level"]))
        if allowed:
            allowed["updated_at"] = datetime.now()
            self.clans.find_one_and_update({"_id": str(clan_id)}, {"$set": allowed})
        return self.read_clan(clan_id)

    # --- Atomic Membership Operations ---
    def add_member_atomic(self, clan_id: str, user_id: str, role: str = "member") -> tuple[bool, str]:
        cid, uid = str(clan_id), str(user_id)
        if self.get_user_membership(uid) is not None:
            return False, "already_in_clan"
        clan = self.read_clan(cid)
        if not clan:
            return False, "clan_not_found"
        max_m = int(clan.get("max_members", DEFAULT_MAX_CLAN_MEMBERS))
        cur_m = int(clan.get("member_count", 0))
        if cur_m >= max_m:
            return False, "clan_full"

        # Atomic conditional capacity increment on clan document
        updated_clan = self.clans.find_one_and_update(
            {"_id": cid, "member_count": {"$lt": max_m}},
            {"$inc": {"member_count": 1}, "$set": {"updated_at": datetime.now()}},
        )
        if updated_clan is None:
            return False, "clan_full"

        now = datetime.now()
        r = role if role in CLAN_ROLE_RANK else "member"
        member_doc = {
            "_id": f"cmem_{cid}_{uid}",
            "clan_id": cid,
            "user_id": uid,
            "role": r,
            "role_rank": CLAN_ROLE_RANK[r],
            "contribution_score": 0,
            "weekly_contribution": 0,
            "monthly_contribution": 0,
            "contribution_xp": 0,
            "matches_played": 0,
            "matches_won": 0,
            "recent_opponents": {},
            "joined_at": now,
            "last_active_at": now,
        }
        try:
            self.members.insert_one(member_doc)
        except Exception:
            self.clans.find_one_and_update({"_id": cid}, {"$inc": {"member_count": -1}})
            return False, "already_in_clan"

        # Cancel any pending join requests or invitations for this user
        self.join_requests.update_many(
            {"user_id": uid, "status": "pending"},
            {"$set": {"status": "closed", "updated_at": now}},
        )
        self.invitations.update_many(
            {"to_user_id": uid, "status": "pending"},
            {"$set": {"status": "accepted", "updated_at": now}},
        )
        return True, "ok"

    def remove_member(self, clan_id: str, user_id: str) -> bool:
        cid, uid = str(clan_id), str(user_id)
        res = self.members.delete_one({"clan_id": cid, "user_id": uid})
        if getattr(res, "deleted_count", 0) > 0:
            actual_cnt = self.members.count_documents({"clan_id": cid})
            self.clans.find_one_and_update(
                {"_id": cid},
                {"$set": {"member_count": max(0, actual_cnt), "updated_at": datetime.now()}},
            )
            return True
        return False

    def set_member_role(self, clan_id: str, user_id: str, new_role: str) -> bool:
        if new_role not in CLAN_ROLE_RANK:
            return False
        self.members.find_one_and_update(
            {"clan_id": str(clan_id), "user_id": str(user_id)},
            {"$set": {"role": new_role, "role_rank": CLAN_ROLE_RANK[new_role]}},
        )
        return True

    def transfer_leadership(self, clan_id: str, old_leader_id: str, new_leader_id: str) -> bool:
        cid, o_id, n_id = str(clan_id), str(old_leader_id), str(new_leader_id)
        target_m = self.members.find_one({"clan_id": cid, "user_id": n_id})
        if not target_m:
            return False
        self.set_member_role(cid, o_id, "co_leader")
        self.set_member_role(cid, n_id, "leader")
        self.clans.find_one_and_update(
            {"_id": cid},
            {"$set": {"leader_id": n_id, "updated_at": datetime.now()}},
        )
        self.log_audit(cid, o_id, "transfer_leadership", n_id)
        return True

    def disband_clan(self, clan_id: str, actor_id: str) -> bool:
        cid = str(clan_id)
        self.members.delete_many({"clan_id": cid})
        self.join_requests.delete_many({"clan_id": cid})
        self.invitations.delete_many({"clan_id": cid})
        self.challenges.delete_many({"clan_id": cid})
        self.log_audit(cid, actor_id, "disband_clan", cid)
        res = self.clans.delete_one({"_id": cid})
        return getattr(res, "deleted_count", 0) > 0

    # --- Join Requests & Invitations ---
    def create_join_request(self, clan_id: str, user_id: str, message: str = "") -> dict:
        cid, uid = str(clan_id), str(user_id)
        existing = self.join_requests.find_one({"clan_id": cid, "user_id": uid, "status": "pending"})
        if existing:
            return existing
        now = datetime.now()
        doc = {
            "_id": f"cjreq_{create_random_name()}",
            "clan_id": cid,
            "user_id": uid,
            "message": str(message or "").strip()[:160],
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        self.join_requests.insert_one(doc)
        return doc

    def read_join_request(self, req_id: str):
        return self.join_requests.find_one({"_id": str(req_id)})

    def get_pending_join_requests(self, clan_id: str) -> list[dict]:
        return list(self.join_requests.find({"clan_id": str(clan_id), "status": "pending"}).sort("created_at", -1))

    def update_join_request_status(self, req_id: str, status: str, reviewer_id: str = ""):
        self.join_requests.find_one_and_update(
            {"_id": str(req_id)},
            {"$set": {"status": status, "reviewer_id": str(reviewer_id), "updated_at": datetime.now()}},
        )

    def create_clan_invitation(self, clan_id: str, from_user_id: str, to_user_id: str) -> dict:
        cid, fid, tid = str(clan_id), str(from_user_id), str(to_user_id)
        existing = self.invitations.find_one({"clan_id": cid, "to_user_id": tid, "status": "pending"})
        if existing:
            return existing
        now = datetime.now()
        doc = {
            "_id": f"cinv_{create_random_name()}",
            "clan_id": cid,
            "from_user_id": fid,
            "to_user_id": tid,
            "status": "pending",
            "created_at": now,
            "expires_at": now + timedelta(days=7),
            "updated_at": now,
        }
        self.invitations.insert_one(doc)
        return doc

    def read_clan_invitation(self, invite_id: str):
        return self.invitations.find_one({"_id": str(invite_id)})

    def get_user_clan_invitations(self, user_id: str) -> list[dict]:
        now = datetime.now()
        cursor = self.invitations.find({"to_user_id": str(user_id), "status": "pending"}).sort("created_at", -1)
        out = []
        for doc in cursor:
            exp = doc.get("expires_at")
            if isinstance(exp, datetime) and exp < now:
                continue
            out.append(doc)
        return out

    def get_clan_outgoing_invitations(self, clan_id: str) -> list[dict]:
        return list(self.invitations.find({"clan_id": str(clan_id), "status": "pending"}).sort("created_at", -1))

    def update_clan_invitation_status(self, invite_id: str, status: str):
        self.invitations.find_one_and_update(
            {"_id": str(invite_id)},
            {"$set": {"status": status, "updated_at": datetime.now()}},
        )

    # --- Clan Competitive Contributions & Challenges (Anti-Farming Enabled) ---
    def record_member_match_contribution(
        self,
        user_id: str,
        is_win: bool,
        score_earned: int = 0,
        xp_earned: int = 0,
        game_type: str = "",
        opponent_ids: list[str] | None = None,
        is_ranked: bool = True,
        **kwargs,
    ) -> dict | None:
        uid = str(user_id)
        if uid.startswith("bot_") or uid.startswith("test_bot"):
            return None
        mem = self.get_user_membership(uid)
        if not mem:
            return None
        cid = str(mem["clan_id"])
        clan = self.read_clan(cid)
        if not clan:
            return None

        now = datetime.now()
        week_key = now.strftime("%Y-W%W")
        month_key = now.strftime("%Y-%m")

        # Anti-farming check: prevent score/XP farming against the exact same opponent > 3 times within 2 hours
        recent_opps: dict = dict(mem.get("recent_opponents", {}) or {})
        cutoff_ts = (now - timedelta(hours=2)).timestamp()
        cleaned_opps: dict = {}
        for k, timestamps in recent_opps.items():
            if isinstance(timestamps, list):
                valid_ts = [float(t) for t in timestamps if float(t) >= cutoff_ts]
                if valid_ts:
                    cleaned_opps[k] = valid_ts

        is_farmed = not bool(is_ranked)
        for opp in (opponent_ids or []):
            opp_s = str(opp)
            if opp_s and opp_s != uid and not opp_s.startswith("bot_"):
                opp_mem = self.get_user_membership(opp_s)
                if opp_mem and str(opp_mem.get("clan_id")) == cid:
                    is_farmed = True
                hist = cleaned_opps.get(opp_s, [])
                if len(hist) >= 3:
                    is_farmed = True
                hist.append(now.timestamp())
                cleaned_opps[opp_s] = hist

        contrib_pts = 0 if is_farmed else max(0, (15 if is_win else 4) + max(0, int(score_earned)))
        contrib_xp = 0 if is_farmed else max(2, int(xp_earned) // 2 + (8 if is_win else 3))

        # Roll over weekly/monthly clan buckets if period changed
        if clan.get("week_key") != week_key:
            self.clans.find_one_and_update(
                {"_id": cid},
                {"$set": {"weekly_score": 0, "week_key": week_key}},
            )
            self.members.update_many({"clan_id": cid}, {"$set": {"weekly_contribution": 0}})
        if clan.get("month_key") != month_key:
            self.clans.find_one_and_update(
                {"_id": cid},
                {"$set": {"monthly_score": 0, "month_key": month_key}},
            )
            self.members.update_many({"clan_id": cid}, {"$set": {"monthly_contribution": 0}})

        self.members.find_one_and_update(
            {"_id": mem["_id"]},
            {
                "$inc": {
                    "contribution_score": contrib_pts,
                    "weekly_contribution": contrib_pts,
                    "monthly_contribution": contrib_pts,
                    "contribution_xp": contrib_xp,
                    "matches_played": 1,
                    "matches_won": 1 if is_win else 0,
                },
                "$set": {
                    "recent_opponents": cleaned_opps,
                    "last_active_at": now,
                },
            },
        )

        new_clan_xp = int(clan.get("clan_xp", 0)) + contrib_xp
        new_clan_lvl = calculate_clan_level(new_clan_xp)
        new_total_wins = int(clan.get("total_wins", 0)) + (1 if is_win else 0)
        achievements = list(clan.get("achievements", []) or [])
        if new_total_wins >= 10 and "clan_10_wins" not in achievements:
            achievements.append("clan_10_wins")
        if new_total_wins >= 50 and "clan_50_wins" not in achievements:
            achievements.append("clan_50_wins")
        if new_clan_lvl >= 3 and "clan_level_3" not in achievements:
            achievements.append("clan_level_3")

        self.clans.find_one_and_update(
            {"_id": cid},
            {
                "$inc": {
                    "clan_score": contrib_pts,
                    "weekly_score": contrib_pts,
                    "monthly_score": contrib_pts,
                    "clan_xp": contrib_xp,
                    "total_matches": 1,
                    "total_wins": 1 if is_win else 0,
                },
                "$set": {
                    "clan_level": new_clan_lvl,
                    "achievements": achievements,
                    "updated_at": now,
                },
            },
        )
        return {
            "clan_id": cid,
            "contrib_pts": contrib_pts,
            "contrib_xp": contrib_xp,
            "clan_level": new_clan_lvl,
            "is_farmed": is_farmed,
        }
