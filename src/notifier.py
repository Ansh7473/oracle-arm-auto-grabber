import datetime
import logging
from typing import Optional
import telebot

class TelegramNotifier:
    def __init__(self, bot_token: Optional[str], uid: Optional[str]):
        self.bot_token = bot_token
        self.uid = uid
        self.bot = telebot.TeleBot(bot_token) if bot_token and uid else None
        self.status_msg_id: Optional[int] = None

    def is_enabled(self) -> bool:
        return self.bot is not None and self.uid is not None

    def send_startup_alert(self, cloud_name: str, ocpus: int, memory_gb: int, display_name: str):
        if not self.is_enabled():
            return
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        text = (
            f"🚀 *OCI ARM Auto-Grabber Started*\n\n"
            f"📌 *Cloud Account:* `{cloud_name}`\n"
            f"⚡ *Target Spec:* `{ocpus} OCPU / {memory_gb} GB RAM`\n"
            f"🏷️ *Instance Name:* `{display_name}`\n"
            f"🕒 *Started:* `{now_str}`\n\n"
            f"🔄 *Status:* Active & Retrying..."
        )
        try:
            msg = self.bot.send_message(self.uid, text, parse_mode="Markdown")
            self.status_msg_id = msg.id
        except Exception as e:
            logging.warning(f"Failed to send Telegram startup message: {e}")

    def update_status(self, cloud_name: str, email: str, retry_count: int):
        if not self.is_enabled() or not self.status_msg_id:
            return
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        text = (
            f"⚡ *OCI ARM Auto-Grabber Status*\n\n"
            f"📌 *Cloud:* `{cloud_name}`\n"
            f"✉️ *User:* `{email}`\n"
            f"🔄 *Total Retries:* `{retry_count}`\n"
            f"🕒 *Last Check:* `{now_str}`\n\n"
            f"🟢 *Bot Status:* Running..."
        )
        try:
            self.bot.edit_message_text(text, self.uid, self.status_msg_id, parse_mode="Markdown")
        except Exception:
            pass

    def send_success_alert(self, cloud_name: str, display_name: str, public_ip: str, total_retries: int):
        if not self.is_enabled():
            return
        text = (
            f"🎉 *ARM Instance Successfully Minted!*\n\n"
            f"🏷️ *Name:* `{display_name}`\n"
            f"🌐 *Public IP:* `{public_ip}`\n"
            f"📌 *Cloud:* `{cloud_name}`\n"
            f"🔄 *Total Retries:* `{total_retries}`\n\n"
            f"✅ *Grabber successfully completed!*"
        )
        try:
            if self.status_msg_id:
                try:
                    self.bot.delete_message(self.uid, self.status_msg_id)
                except Exception:
                    pass
            self.bot.send_message(self.uid, text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to send success Telegram alert: {e}")
