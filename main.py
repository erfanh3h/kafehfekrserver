import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
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
)
from Entities.Database import game_database
from Entities.Database.backup import start_timer as backup_timer

app = FastAPI(
    title="Cafe Fekr Server API & Admin Panel",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Enable CORS for the Admin Panel frontend and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "server"}

app.include_router(admin_router.router)
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(general_router.router)
app.include_router(social_router.router)
app.include_router(clan_router.router)
app.include_router(messaging_router.router)
app.include_router(notification_router.router)

# Mount static build of the Admin Panel if available
admin_static_dir = os.path.join(os.path.dirname(__file__), "static", "admin")
if os.path.exists(admin_static_dir):
    app.mount("/admin-ui", StaticFiles(directory=admin_static_dir, html=True), name="admin_ui")

    @app.get("/admin-panel")
    async def redirect_to_admin_ui():
        return RedirectResponse(url="/admin-ui/")

game_database.check_create_collections()
backup_timer()

if __name__ == '__main__':
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host=host, port=port)
