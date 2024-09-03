from fastapi import HTTPException, status


class HttpExceptions:
    def raise401(self, details=None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=details if details is not None else 'لطفامجددا به حساب خود وارد شوید',
        )

    def raise403(self, details=None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=details if details is not None else 'خطای دسترسی',
        )

    def raise404(self, details=None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=details if details is not None else 'چنین داده ای پیدا نشد',
        )

    def raise409(self, details=None):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=details if details != None else 'این آیدی قبلا ثبت شده است',
        )

    def raise413(self, details=None):
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=details if details != None else 'حجم فایل انتخاب شده بیشتر از حدمجاز است',
        )

    def raise422(self, details=None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=details if details != None else 'کد وارد شده صحیح نمی باشد',
        )
