import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv("/opt/oracle-python-grabber/.env")

bot_token = os.getenv("BOT_TOKEN")
uid = os.getenv("UID")
log_path = "/var/log/oci-python-grabber.log"

if not bot_token or not uid or bot_token == "xxxx":
    sys.exit(0)

if not os.path.exists(log_path):
    logs_text = "No logs recorded yet."
else:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line for line in f.readlines() if line.strip()]
        last_10 = lines[-10:] if len(lines) >= 10 else lines
        logs_text = "".join(last_10).strip()

if len(logs_text) > 3500:
    logs_text = logs_text[-3500:]

msg = f"📊 *OCI ARM Grabber - Hourly Log Report*\n\n```\n{logs_text}\n```"

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
try:
    resp = requests.post(url, data={"chat_id": uid, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    print("Report sent:", resp.status_code)
except Exception as e:
    print("Failed to send report:", e)
