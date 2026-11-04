import threading
import time
from datetime import datetime

from ippanel import Client
from Commons import static_functions


class SMSPanel:

    def __init__(self):
        self.api_key = "Vl5EGLsFoPyekCvlppXSTz1c592WVuElUYHECMvK8m4="
        self.sms_panel = Client(self.api_key)
        self.numbers_to_codes = {}
        self._lock = threading.Lock()

    def start_timer(self):
        def entrypoint():  # this use to auto delete unused keys
            while True:
                time.sleep(300)
                try:
                    now = datetime.now()
                    with self._lock:
                        expired_keys = [
                            key for key, value in self.numbers_to_codes.items()
                            if (now - value[1]).total_seconds() >= 5 * 60
                        ]
                        for key in expired_keys:
                            self.numbers_to_codes.pop(key, None)
                except Exception as e:
                    print(f"[SMSPanel] Error cleaning expired OTPs: {e}")

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def send_code_to_user(self, user_number):
        phone_clean = static_functions.clean_phone_number(user_number)
        if not phone_clean:
            print(f"[SMSPanel] Invalid phone number provided: {user_number}")
            return False

        try:
            code = static_functions.create_random_code()
            with self._lock:
                self.numbers_to_codes[phone_clean] = (code, datetime.now())

            print(f"[SMSPanel] Sending OTP code {code} to {phone_clean}...")
            res_id = self.sms_panel.send_pattern(
                "ccnmmdqhf3hb0h7",  # pattern code
                "+983000505",  # originator / sender
                recipient=phone_clean,
                values={"c": code}
            )
            print(f"[SMSPanel] OTP {code} sent successfully to {phone_clean} (message_id: {res_id})")
            return True
        except Exception as e:
            print(f"[SMSPanel] Failed to send SMS to {phone_clean}: {e}")
            return False

    def check_code(self, user_number, code):
        try:
            phone_clean = static_functions.clean_phone_number(user_number)
            code_clean = static_functions.clean_code(code)
            if not phone_clean or not code_clean:
                return False

            # Allow test bot phone(s) with master code "1234"
            if phone_clean == "09131234567" and code_clean == "1234":
                print(f"[SMSPanel] Test bot {phone_clean} authenticated via master code.")
                return True

            with self._lock:
                entry = self.numbers_to_codes.get(phone_clean)
                if not entry:
                    print(f"[SMSPanel] No pending OTP found for {phone_clean}")
                    return False

                saved_code, send_time = entry
                if (datetime.now() - send_time).total_seconds() > 5 * 60:
                    self.numbers_to_codes.pop(phone_clean, None)
                    print(f"[SMSPanel] OTP expired for {phone_clean}")
                    return False

                if saved_code == code_clean:
                    self.numbers_to_codes.pop(phone_clean, None)
                    print(f"[SMSPanel] OTP verified successfully for {phone_clean}")
                    return True
                else:
                    print(f"[SMSPanel] OTP mismatch for {phone_clean}: expected {saved_code}, got {code_clean}")
                    return False
        except Exception as e:
            print(f"[SMSPanel] Error checking code for {user_number}: {e}")
            return False
