import os
from fastapi import FastAPI
import uvicorn
from Routers import admin_router, auth_router, user_router, general_router, social_router, clan_router, messaging_router, notification_router
from Entities.Database import game_database
from Entities.Database.backup import start_timer as backup_timer

app = FastAPI(docs_url=None, redoc_url=None)

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

game_database.check_create_collections()
backup_timer()

if __name__ == '__main__':
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host=host, port=port)

# {
#   "userId": "66055a02bb412d334272",
#   "phone": "+989377804649"
# }