# Oracle Cloud Always-Free ARM Instance Auto-Grabber v2.1

An automated, production-ready Python tool designed to solve Oracle Cloud's persistent **"Out of Host Capacity"** (HTTP 500 / HTTP 429) errors. It continuously requests and claims Always Free **Ampere A1 Compute Instances** (`VM.Standard.A1.Flex`) in high-demand regions (e.g. Hyderabad, Mumbai, Ashburn, Tokyo) the instant server capacity becomes available.

### ❓ Why This Script Is Needed
Oracle Cloud's Always Free ARM Ampere servers are extremely popular, resulting in continuous **Out of Host Capacity** errors when attempting to create instances manually via the Web Console. This auto-grabber runs 24/7 in the background with adaptive backoff to capture open capacity as soon as another user releases resources or Oracle provisions new hardware.

---

## ⚡ Features & Improvements in v2.1

- **Randomized Jitter (Anti-Collision)**: Adds random 2–8s jitter to retry intervals to prevent collision with other scripts.
- **Smart Error Classification**:
  - `Capacity (500)` -> Continuous retry.
  - `Rate Limit (429)` -> Auto-increasing backoff.
  - `Fatal Errors (400, 401, 403, 404, Bad Credentials)` -> Instantly stops and alerts via Telegram to prevent infinite looping on broken configs.
- **Multi-Image Round-Robin Rotation**: Alternates between multiple image OCIDs (e.g. Oracle Linux 9.8 and Ubuntu 24.04 Minimal) on each retry attempt.
- **Preflight Quota Checks**: Verifies account Always-Free limits (up to 4 OCPUs, 24 GB RAM, 200 GB Storage) before launching.
- **Telegram Notifications**: Real-time Telegram alerts for startup, continuous status updates, and instant notifications upon successful instance minting.
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
git clone https://github.com/Ansh7473/oracle-arm-auto-grabber.git
cd oracle-arm-auto-grabber

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
DISPLAY_NAME=your_instance_display_name_here
COMPARTMENT_ID=ocid1.tenancy.oc1..aaaaaaaaxxxx
SUBNET_ID=ocid1.subnet.oc1.ap-hyderabad-1.aaaaaaaaxxxx
SSH_AUTHORIZED_KEYS=ssh-rsa AAAAB3NzaC1yc2E...
IMAGE_ID=ocid1.image.oc1.ap-hyderabad-1.aaaaaaaaxxxx
BOOT_VOLUME_SIZE_IN_GBS=100

BOT_TOKEN=your_telegram_bot_token_here
UID=your_telegram_chat_id_here

OCPUS=1
MEMORY_IN_GBS=6
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
Restart=on-failure
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
