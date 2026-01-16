import requests
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramNotify:
    def __init__(self, token=None, chat_id=None):
        self.token = os.getenv("TELEGRAM_TOKEN") if os.getenv("TELEGRAM_TOKEN") else token
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID") if os.getenv("TELEGRAM_CHAT_ID") else chat_id

        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0

    def send_message(self, text):
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Telegram gönderme hatası: {e}")

    def get_latest_commands(self):
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 10}
            response = requests.get(url, params=params).json()

            commands = []
            if response.get("ok"):
                for update in response["result"]:
                    self.last_update_id = update["update_id"]
                    if "message" in update and "text" in update["message"]:
                        if str(update["message"]["chat"]["id"]) == self.chat_id:
                            commands.append(update["message"]["text"].upper().strip())
            return commands
        except Exception as e:
            print(f"Telegram okuma hatası: {e}")
            return []

    def send_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                self.send_message("Log dosyası henüz oluşmamış.")
                return

            url = f"{self.base_url}/sendDocument"
            with open(file_path, 'rb') as f:
                payload = {"chat_id": self.chat_id}
                files = {"document": f}
                requests.post(url, data=payload, files=files)
        except Exception as e:
            print(f"Dosya gönderme hatası: {e}")
            self.send_message(f"Dosya gönderilemedi: {e}")