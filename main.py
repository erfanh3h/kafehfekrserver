from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/")
async def root():
    from Entities.Security.sms_panel import SMSPanel
    sms = SMSPanel("ErfanH3h", "199977")
    print(sms.send_code_to_user(user_number="09377804649"))
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5001)
