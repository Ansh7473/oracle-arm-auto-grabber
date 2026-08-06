import logging
import os
import sys
import time
import oci

from src.config import Config
from src.notifier import TelegramNotifier
from src.oci_engine import OCIEngine

LOG_FILE = "/var/log/oci-python-grabber.log"
LOG_FORMAT = "[%(levelname)s] %(asctime)s - %(message)s"

def setup_logging():
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        f_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        f_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(f_handler)
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=handlers
    )

def main():
    setup_logging()
    logging.info("=====================================================")
    logging.info("   OCI ARM Instance Auto-Grabber Engine v2.0")
    logging.info("=====================================================")

    cfg = Config.from_env()
    notifier = TelegramNotifier(cfg.bot_token, cfg.uid)
    engine = OCIEngine(cfg)

    engine.run_preflight_checks()

    notifier.send_startup_alert(
        cloud_name=engine.cloud_name,
        ocpus=cfg.ocpus,
        memory_gb=cfg.memory_in_gbs,
        display_name=cfg.display_name
    )

    retry_count = 0
    wait_time = cfg.minimum_time_interval
    j_count = 0

    while True:
        for ad in cfg.availability_domains:
            retry_count += 1
            j_count += 1

            if j_count >= 10:
                j_count = 0
                notifier.update_status(engine.cloud_name, engine.email, retry_count)

            try:
                public_ip = engine.launch_instance(ad)
                logging.info(f"🎉 SUCCESS! Created '{cfg.display_name}' in {ad}! IP: {public_ip}")
                notifier.send_success_alert(
                    cloud_name=engine.cloud_name,
                    display_name=cfg.display_name,
                    public_ip=public_ip or "N/A",
                    total_retries=retry_count
                )
                sys.exit(0)

            except oci.exceptions.ServiceError as err:
                if err.status == 429:
                    wait_time = min(wait_time + 2, 60)
                    logging.info(
                        f"Attempt #{retry_count} [{ad}] - Rate Limited (429): {err.message} "
                        f"| Backoff Sleep: {wait_time}s"
                    )
                elif err.status == 500 or "capacity" in err.message.lower():
                    wait_time = cfg.minimum_time_interval
                    logging.info(
                        f"Attempt #{retry_count} [{ad}] - Out of Capacity (500): {err.message} "
                        f"| Retrying in {wait_time}s"
                    )
                else:
                    logging.warning(
                        f"Attempt #{retry_count} [{ad}] - OCI Error {err.status} [{err.code}]: {err.message} "
                        f"| Retrying in {wait_time}s"
                    )
                time.sleep(wait_time)

            except Exception as ex:
                logging.error(f"Attempt #{retry_count} [{ad}] - Unexpected Error: {ex} | Retrying in {wait_time}s")
                time.sleep(wait_time)

            except KeyboardInterrupt:
                logging.info("Grabber process manually stopped by user. Exiting.")
                sys.exit(0)

if __name__ == "__main__":
    main()
