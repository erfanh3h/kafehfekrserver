from fastapi import FastAPI, BackgroundTasks, Form, Header, Depends
import uvicorn
from Entities.Api_Services import get_current_user
from Entities import Network_Exeptions

app = FastAPI()


@app.get("/")
async def root():
    from Entities.Security.sms_panel import SMSPanel
    sms = SMSPanel("ErfanH3h", "199977")
    print(sms.send_code_to_user(user_number="09377804649"))
    return {"message": "Hello World"}


@app.post("/enter")
async def enter_user(background_tasks: BackgroundTasks, phone: str = Form(...)):
    # from Entities.Security.sms_panel import SMSPanel
    # smsPanel = SMSPanel("ErfanH3h", "199977")
    # print(sms.send_code_to_user(user_number="09377804649"))
    from Entities.Api_Services import auth
    if auth.check_not_in_game(phone):
        # background_tasks.add_task(smsPanel.send_code_to_user, phone, "")
        return {"result": True}
    else:
        raise Network_Exeptions.raise403(details="بازیکن در بازی است و نمیتواند وارد شود")


@app.post("/code")
async def enter_code(phone: str = Form(...), code: str = Form(...)):
    # from Entities.Security.sms_panel import SMSPanel
    # sms = SMSPanel("ErfanH3h", "199977")
    # if sms.check_code(user_number=phone, code=code):
    if code == "123456":
        from Entities.Api_Services import auth
        from Entities import Security
        user_data = auth.enter_user(phone)
        token = Security.create_access_token(
            data={'phone': phone, 'id': user_data['_id'], 'device_id': user_data['device_id']})
        print(await Security.extract_token(token))
        return {"user_data": user_data, "token": token}
    else:
        raise Network_Exeptions.raise422()


@app.post("/complete-data")
async def complete_user(authorization: str = Header(...), user=Depends(get_current_user), username: str = Form(...),
                        device_id: str = Form(...), ):
    from Entities.Api_Services import auth
    auth.complete_user(user['_id'], username, device_id)
    return {"message": "Hello World"}


@app.get("/my-data")
async def say_hello(authorization: str = Header(...), user=Depends(get_current_user)):
    return {"result": user}


@app.get("/my-history")
async def say_hello(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.user_histories(user_data['_id'])}


@app.get("/my-game-history")
async def say_hello(authorization: str = Header(...), user_data=Depends(get_current_user)):
    from Entities.Api_Services import user
    return {"result": user.user_game_histories(user_data['_id'])}


@app.get("/user-data")
async def say_hello(userid: str, authorization: str = Header(...), user=Depends(get_current_user)):
    return {"result": userid}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)
