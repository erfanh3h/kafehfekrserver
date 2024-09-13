from fastapi import APIRouter, BackgroundTasks, Form, Header, Depends

from Entities import Network_Exeptions
from Entities.Api_Services import get_current_user
from Entities.Security.sms_panel import SMSPanel

router = APIRouter(prefix='', tags=['auth'])

sms_panel = SMSPanel()
sms_panel.start_timer()


@router.post("/enter")
async def enter_user(background_tasks: BackgroundTasks, phone: str = Form(...)):
    from Entities.Api_Services import auth
    if auth.check_not_in_game(phone):
        # background_tasks.add_task(sms_panel.send_code_to_user, phone)
        return {"result": True}
    else:
        raise Network_Exeptions.raise403(details="بازیکن در بازی است و نمیتواند وارد شود")


@router.post("/code")
async def enter_code(phone: str = Form(...), code: str = Form(...), device_id: str = Form(...)):
    # if sms_panel.check_code(user_number=phone, code=code):
    if code == "1234":
        from Entities.Api_Services import auth
        from Entities import Security
        user_data = auth.enter_user(phone, device_id)
        print(user_data['device_id'])
        token = Security.create_access_token(
            data={'phone': phone, 'id': user_data['_id'], 'device_id': device_id})
        print(await Security.extract_token(token))
        return {"user_data": user_data, "token": token}
    else:
        raise Network_Exeptions.raise422()


@router.post("/complete-data")
async def complete_user(authorization: str = Header(...), user=Depends(get_current_user), username: str = Form(...)):
    from Entities.Api_Services import auth
    auth.complete_user(user['_id'], username)
    return {"result": True}
