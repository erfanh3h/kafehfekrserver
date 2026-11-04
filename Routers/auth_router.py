from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Form, Header, Depends

from Entities import Network_Exeptions
from Entities.Api_Services import get_current_user
from Entities.Security.sms_panel import SMSPanel
from Commons import static_functions

router = APIRouter(prefix='', tags=['auth'])

sms_panel = SMSPanel()
sms_panel.start_timer()


@router.post("/enter")
async def enter_user(background_tasks: BackgroundTasks, phone: str = Form(...)):
    from Entities.Api_Services import auth
    clean_phone = static_functions.clean_phone_number(phone)
    if not clean_phone or len(clean_phone) < 10:
        raise Network_Exeptions.raise422(details="شماره موبایل وارد شده معتبر نمی باشد")

    if auth.check_not_in_game(clean_phone):
        background_tasks.add_task(sms_panel.send_code_to_user, clean_phone)
        return {"result": True}
    else:
        raise Network_Exeptions.raise403(details="بازیکن در بازی است و نمیتواند وارد شود")


@router.post("/code")
async def enter_code(phone: str = Form(...), code: str = Form(...), device_id: str = Form(...)):
    clean_phone = static_functions.clean_phone_number(phone)
    if not clean_phone:
        raise Network_Exeptions.raise422(details="شماره موبایل وارد شده معتبر نمی باشد")

    if sms_panel.check_code(user_number=clean_phone, code=code):
        from Entities.Api_Services import auth
        from Entities import Security
        user_data = auth.enter_user(clean_phone, device_id)
        if not user_data:
            raise Network_Exeptions.raise422(details="User could not be found or registered")
        print(user_data.get('device_id', ''))
        token = Security.create_access_token(
            data={'phone': clean_phone, 'id': user_data['_id'], 'device_id': device_id})
        print(await Security.extract_token(token))
        return {"user_data": user_data, "token": token}
    else:
        raise Network_Exeptions.raise422(details="کد تأیید وارد شده اشتباه یا منقضی شده است")


@router.post("/complete-data")
async def complete_user(authorization: str = Header(...), user=Depends(get_current_user), username: str = Form(...),
                        rep_id: Optional[str] = Form(None)):
    from Entities.Api_Services import auth
    auth.complete_user(user['_id'], username, rep_id)
    return {"result": True}
