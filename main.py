from fastapi import FastAPI, BackgroundTasks, Form, Header, Depends
import uvicorn
from Entities.Api_Services import get_current_user

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
    # sms = SMSPanel("ErfanH3h", "199977")
    # print(sms.send_code_to_user(user_number="09377804649"))
    # from Entities.Api_Services import auth
    # auth.enter_user(phone)
    # background_tasks.add_task(smsPanel.AutoSendCode, phone, "")
    return {"message": f"Hello {phone}"}


@app.post("/code")
async def enter_user(phone: str = Form(...), code: str = Form(...)):
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
    return {"message": "Bad code"}


@app.post("/complete-data")
async def complete_user(authorization: str = Header(...), user=Depends(get_current_user), username: str = Form(...),
                        device_id: str = Form(...), ):
    from Entities.Api_Services import auth
    auth.complete_user(user['_id'], username, device_id)
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)
