# Oracle Cloud Always-Free ARM Instance Auto-Grabber v2.0

An automated, production-ready Python tool built to continuously request and claim Oracle Cloud Always Free **Ampere A1 Compute Instances** (`VM.Standard.A1.Flex`) in high-demand regions (e.g. Hyderabad, Mumbai, Ashburn, Tokyo) as soon as host capacity opens up.

---

## ⚡ Features

- **Automated Retry Loop**: Automatically retries instance launch requests with intelligent backoff.
- **Smart Adaptive Rate-Limiting**: Handles HTTP 429 throttling and HTTP 500 Out of Host Capacity errors without crashing.
- **Preflight Quota Checks**: Verifies account Always-Free limits (4 OCPUs, 24 GB RAM, 200 GB Storage) before launching.
- **Telegram Notifications**: Real-time Telegram alerts for startup, continuous status updates, and instant notifications upon successful instance minting.
- **Automated Hourly Reports**: Optional cron job for sending the last 10 log entries directly to Telegram every hour.
- **Systemd Service Integration**: Runs quietly 24/7 in the background on any Linux VPS or micro instance.

---

## 🏗️ Architecture & File Structure

```text
oci-arm-grabber/
├── src/
│   ├── config.py         # Structured dataclass environment configuration loader
│   ├── notifier.py       # Telegram bot notification & status update manager
│   ├── oci_engine.py     # OCI SDK client wrapper, preflight checks & launch handler
│   └── main.py           # Main engine loop & entry point
├── bot.py                # Legacy single-script entry point
├── hourly_report.py      # Hourly log summary Telegram reporter
├── setup_py_env.sh       # Quick setup script for environment configuration
├── requirements.txt      # Python dependencies
├── .env.example          # Sample environment configuration template
└── README.md             # Documentation
```

---

## 🛠️ Quick Installation

### 1. Clone Repository & Setup Virtual Environment

```bash
git clone https://github.com/Ansh7473/oracle-out-of-capacity-grabber.git
cd oracle-out-of-capacity-grabber

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Copy `.env.example` to `.env` and fill in your Oracle Cloud OCIDs:

```bash
cp .env.example .env
nano .env
```

Example `.env` configuration:

```env
AVAILABILITY_DOMAINS=wrEQ:AP-HYDERABAD-1-AD-1
DISPLAY_NAME=free-arm-12gb
COMPARTMENT_ID=ocid1.tenancy.oc1..aaaaaaaaxxxx
SUBNET_ID=ocid1.subnet.oc1.ap-hyderabad-1.aaaaaaaaxxxx
SSH_AUTHORIZED_KEYS=ssh-rsa AAAAB3NzaC1yc2E...
IMAGE_ID=ocid1.image.oc1.ap-hyderabad-1.aaaaaaaaxxxx
BOOT_VOLUME_SIZE_IN_GBS=100

BOT_TOKEN=your_telegram_bot_token_here
UID=your_telegram_chat_id_here

OCPUS=2
MEMORY_IN_GBS=12
MINIMUM_TIME_INTERVAL=35
```

---

## ⚙️ Running as a Systemd Service

To run 24/7 in the background:

```bash
cat <<EOF | sudo tee /etc/systemd/system/oci-python-grabber.service
[Unit]
Description=Oracle Cloud Python Out of Capacity Grabber
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/oracle-python-grabber
ExecStart=/opt/oracle-python-grabber/venv/bin/python3 -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable oci-python-grabber --now
```

### Check Logs Live
```bash
sudo tail -f /var/log/oci-python-grabber.log
```

---

## 📊 Hourly Telegram Log Reports

To receive hourly log summaries in Telegram, add this cron job:

```bash
(crontab -l 2>/dev/null; echo "0 * * * * /opt/oracle-python-grabber/venv/bin/python3 /opt/oracle-python-grabber/hourly_report.py >> /var/log/oci-python-report.log 2>&1") | crontab -
```

---

## 📄 License

MIT License © 2026 Ansh7473
