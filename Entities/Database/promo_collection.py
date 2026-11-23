import secrets
import string
from datetime import datetime, timezone
from fastapi import HTTPException
from Commons.static_functions import _parse_utc_datetime


def _generate_redemption_id() -> str:
    alphabet = string.ascii_letters + string.digits
    return "rdm_" + "".join(secrets.choice(alphabet) for _ in range(10))


class PromoCollectionManager:
    """Manages promotional gift codes and atomic player redemptions."""

    def __init__(self, codes_collection, redemptions_collection):
        self.codes = codes_collection
        self.redemptions = redemptions_collection
        try:
            self.codes.create_index("code", unique=True)
            self.redemptions.create_index([("promo_id", 1), ("user_id", 1)])
        except Exception:
            pass

    def redeem_code(self, user_id: str, raw_code: str, users_collection) -> dict:
        clean_code = str(raw_code or "").strip().upper()
        if not clean_code or len(clean_code) < 3:
            raise HTTPException(status_code=400, detail="کد هدیه وارد شده نامعتبر است.")

        promo = self.codes.find_one({"code": clean_code})
        if not promo:
            raise HTTPException(status_code=404, detail="کد هدیه یافت نشد.")

        if not promo.get("is_active", True):
            raise HTTPException(status_code=400, detail="این کد هدیه غیرفعال شده است.")

        expires_at = _parse_utc_datetime(promo.get("expires_at"))
        if expires_at is not None and datetime.now(timezone.utc) >= expires_at:
            raise HTTPException(status_code=400, detail="مهلت استفاده از این کد هدیه به پایان رسیده است.")

        promo_id = str(promo["_id"])
        per_user_limit = max(1, int(promo.get("per_user_limit", 1) or 1))
        user_uses = self.redemptions.count_documents({"promo_id": promo_id, "user_id": str(user_id)})
        if user_uses >= per_user_limit:
            raise HTTPException(status_code=400, detail="شما قبلاً از این کد هدیه استفاده کرده‌اید.")

        max_uses = int(promo.get("max_uses", 0) or 0)
        inc_filter: dict = {"_id": promo["_id"], "is_active": True}
        if max_uses > 0:
            inc_filter["used_count"] = {"$lt": max_uses}

        updated_promo = self.codes.find_one_and_update(
            inc_filter,
            {"$inc": {"used_count": 1}},
        )
        if not updated_promo:
            raise HTTPException(status_code=400, detail="ظرفیت استفاده از این کد هدیه تکمیل شده است.")

        reward_coin = max(0, int(promo.get("reward_coin", 0) or 0))
        reward_xp = max(0, int(promo.get("reward_xp", 0) or 0))

        inc_fields = {}
        if reward_coin > 0:
            inc_fields["coin"] = reward_coin
        if reward_xp > 0:
            inc_fields["xp"] = reward_xp

        if inc_fields and users_collection is not None:
            users_collection.update_one({"_id": str(user_id)}, {"$inc": inc_fields})

        updated_user = users_collection.find_one({"_id": str(user_id)}, {"coin": 1, "xp": 1}) if users_collection is not None else {}
        now = datetime.now(timezone.utc)
        redemption_doc = {
            "_id": _generate_redemption_id(),
            "promo_id": promo_id,
            "code": clean_code,
            "user_id": str(user_id),
            "reward_coin": reward_coin,
            "reward_xp": reward_xp,
            "redeemed_at": now,
        }
        self.redemptions.insert_one(redemption_doc)

        return {
            "ok": True,
            "code": clean_code,
            "title": str(promo.get("title") or clean_code),
            "reward_coin": reward_coin,
            "reward_xp": reward_xp,
            "new_coin": int((updated_user or {}).get("coin", 0) or 0),
            "new_xp": int((updated_user or {}).get("xp", 0) or 0),
            "message": "کد هدیه با موفقیت اعمال شد!",
        }
