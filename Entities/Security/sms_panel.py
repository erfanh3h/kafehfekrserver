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

    def start_timer(self):
        def entrypoint():  # this use to auto delete unused keys
            while True:
                remove_list = []
                try:
                    for key, value in self.numbers_to_codes.items():
                        diff = (datetime.now() - value[1]).seconds
                        print(diff)
                        if diff >= 5 * 60:
                            remove_list.append(key)
                except:
                    pass
                for key in remove_list:
                    try:
                        del self.numbers_to_codes[key]
                    except:
                        pass
                time.sleep(300)

        t = threading.Thread(target=entrypoint, daemon=True)
        t.start()

    def send_code_to_user(self, user_number):
        try:
            code = static_functions.create_random_code()
            self.numbers_to_codes[user_number] = (code, datetime.now())
            self.sms_panel.send_pattern(
                "w12zv0tnr93m2tq",  # originator
                "+983000505",  # recipients
                recipient=user_number,
                values={"c": code}
            )
        except:
            pass

    def check_code(self, user_number, code):
        try:
            result = self.numbers_to_codes[user_number][0] == code
            if result:
                del self.numbers_to_codes[user_number]
            return result
        except:
            return False
