from fastapi import FastAPI
import uvicorn
from Routers import admin_router, auth_router, user_router, general_router
from Entities.Database import game_database
from Entities.Database.backup import start_timer as backup_timer

app = FastAPI(docs_url=None, redoc_url=None)

app.include_router(admin_router.router)
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(general_router.router)

game_database.check_create_collections()
backup_timer()

# from Entities.Api_Services import user
# print(user.purchase("hGSOlz", "1", "Bazaar", "22026177", 0))
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)
