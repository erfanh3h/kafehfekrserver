import os
import time
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
import uvicorn
from Routers import (
    admin_router,
    auth_router,
    user_router,
    general_router,
    social_router,
    clan_router,
    messaging_router,
    notification_router,
    spectator_router,
)
from Entities.Database import game_database
from Entities.Database.backup import start_timer as backup_timer
from Entities.Security import SECRET_KEY

SERVER_STARTED_AT = time.time()

app = FastAPI(docs_url=None, redoc_url=None)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "server", "uptime_seconds": int(time.time() - SERVER_STARTED_AT)}


@app.get("/internal/admin/health-stats")
async def internal_admin_health_stats(x_internal_secret: str = Header(default="")):
    if x_internal_secret != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

    mongo_ok = False
    mongo_ping_ms = None
    try:
        t0 = time.perf_counter()
        game_database.db_client.admin.command("ping")
        mongo_ping_ms = round((time.perf_counter() - t0) * 1000, 2)
        mongo_ok = True
    except Exception:
        mongo_ok = False

    cfg = {}
    try:
        cfg = game_database.config_manager.read_config() or {}
    except Exception:
        cfg = {}

    return {
        "ok": True,
        "status": "ok" if mongo_ok else "degraded",
        "service": "server",
        "uptime_seconds": int(time.time() - SERVER_STARTED_AT),
        "mongo_ok": mongo_ok,
        "mongo_ping_ms": mongo_ping_ms,
        "maintenance_mode": bool(cfg.get("maintenance_mode", False)),
        "is_queue_open": bool(cfg.get("is_queue_open", True)),
    }


app.include_router(admin_router.router)
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(general_router.router)
app.include_router(social_router.router)
app.include_router(clan_router.router)
app.include_router(messaging_router.router)
app.include_router(notification_router.router)
app.include_router(spectator_router.router)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

game_database.check_create_collections()
backup_timer()

if __name__ == '__main__':
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host=host, port=port)