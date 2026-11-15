from datetime import datetime
import pymongo
from Commons.static_functions import create_random_user_id


DEFAULT_ADMIN_PERMISSIONS = [
    "dashboard:read",
    "users:read",
    "users:write",
    "games:read",
    "games:manage",
    "config:read",
    "config:write",
    "economy:read",
    "economy:write",
    "clans:read",
    "clans:manage",
    "reports:read",
    "reports:manage",
    "admins:manage",
    "system:backup",
]

ROLE_PERMISSIONS = {
    "superadmin": ["*"],
    "admin": [
        "dashboard:read",
        "users:read",
        "users:write",
        "games:read",
        "games:manage",
        "config:read",
        "config:write",
        "economy:read",
        "economy:write",
        "clans:read",
        "clans:manage",
        "reports:read",
        "reports:manage",
        "system:backup",
    ],
    "moderator": [
        "dashboard:read",
        "users:read",
        "users:write",
        "games:read",
        "clans:read",
        "reports:read",
        "reports:manage",
    ],
    "support": [
        "dashboard:read",
        "users:read",
        "games:read",
        "reports:read",
    ],
}


class AdminCollectionManager:
    """Manages administrative users and permissions in MongoDB."""

    def __init__(self, collection):
        self.collection = collection
        self.ensure_indexes()

    def ensure_indexes(self):
        try:
            self.collection.create_index([("username", pymongo.ASCENDING)], unique=True)
            self.collection.create_index([("is_active", pymongo.ASCENDING)])
            self.collection.create_index([("role", pymongo.ASCENDING)])
        except Exception as e:
            print(f"[AdminCollection] Index creation note: {e}")

    def create_admin(
        self,
        username: str,
        password_hash: str,
        full_name: str = "",
        role: str = "admin",
        permissions: list | None = None,
        created_by: str = "system",
    ) -> dict | None:
        clean_user = str(username or "").strip().lower()
        if not clean_user or len(clean_user) < 3:
            raise ValueError("نام کاربری ادمین باید حداقل ۳ کاراکتر باشد.")

        if self.find_by_username(clean_user):
            raise ValueError(f"ادمین با نام کاربری '{clean_user}' قبلاً ایجاد شده است.")

        clean_role = role if role in ROLE_PERMISSIONS else "admin"
        if permissions is None:
            effective_perms = ROLE_PERMISSIONS.get(clean_role, ROLE_PERMISSIONS["admin"])
        else:
            effective_perms = list(permissions)

        admin_id = f"adm_{create_random_user_id(length=8)}"
        doc = {
            "_id": admin_id,
            "username": clean_user,
            "password_hash": password_hash,
            "full_name": str(full_name or clean_user).strip(),
            "role": clean_role,
            "permissions": effective_perms,
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None,
            "created_by": str(created_by or "system"),
        }
        self.collection.insert_one(doc)
        return self._sanitize_admin(doc)

    def find_by_username(self, username: str) -> dict | None:
        clean_user = str(username or "").strip().lower()
        if not clean_user:
            return None
        return self.collection.find_one({"username": clean_user})

    def find_by_id(self, admin_id: str) -> dict | None:
        if not admin_id:
            return None
        return self.collection.find_one({"_id": str(admin_id)})

    def list_admins(self, include_inactive: bool = True) -> list[dict]:
        query = {} if include_inactive else {"is_active": True}
        cursor = self.collection.find(query).sort([("created_at", pymongo.DESCENDING)])
        return [self._sanitize_admin(doc) for doc in cursor]

    def update_admin(
        self,
        admin_id: str,
        full_name: str | None = None,
        role: str | None = None,
        permissions: list | None = None,
        is_active: bool | None = None,
        password_hash: str | None = None,
    ) -> dict | None:
        aid = str(admin_id)
        existing = self.find_by_id(aid)
        if not existing:
            return None

        update_fields = {}
        if full_name is not None:
            update_fields["full_name"] = str(full_name).strip()
        if role is not None and role in ROLE_PERMISSIONS:
            update_fields["role"] = role
            if permissions is None:
                update_fields["permissions"] = ROLE_PERMISSIONS[role]
        if permissions is not None:
            update_fields["permissions"] = list(permissions)
        if is_active is not None:
            update_fields["is_active"] = bool(is_active)
        if password_hash is not None:
            update_fields["password_hash"] = password_hash

        if update_fields:
            self.collection.find_one_and_update({"_id": aid}, {"$set": update_fields})
        return self._sanitize_admin(self.find_by_id(aid))

    def update_last_login(self, admin_id: str):
        self.collection.find_one_and_update(
            {"_id": str(admin_id)},
            {"$set": {"last_login": datetime.now()}}
        )

    def delete_admin(self, admin_id: str) -> bool:
        res = self.collection.delete_one({"_id": str(admin_id)})
        return res.deleted_count > 0

    def count_admins(self) -> int:
        return self.collection.count_documents({})

    def ensure_default_superadmin(self, default_username: str = "admin", default_pass: str = "admin123456"):
        if self.count_admins() == 0:
            from Entities.Security import hash_admin_password
            hashed = hash_admin_password(default_pass)
            self.create_admin(
                username=default_username,
                password_hash=hashed,
                full_name="مدیر کل کافه فکر",
                role="superadmin",
                permissions=["*"],
                created_by="system_auto_seed",
            )
            print(f"[Admin] Default superadmin created successfully: username='{default_username}', password='{default_pass}'. Change this in admin panel!")

    @staticmethod
    def _sanitize_admin(doc: dict | None) -> dict | None:
        if not doc:
            return None
        safe = dict(doc)
        safe.pop("password_hash", None)
        c_at = safe.get("created_at")
        l_in = safe.get("last_login")
        safe["created_at"] = c_at.isoformat() if hasattr(c_at, "isoformat") else str(c_at or "")
        safe["last_login"] = l_in.isoformat() if hasattr(l_in, "isoformat") else (str(l_in) if l_in else None)
        return safe
