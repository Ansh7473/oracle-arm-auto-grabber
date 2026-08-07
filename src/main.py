import logging
import os
import random
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
    logging.info("   OCI ARM Instance Auto-Grabber Engine v2.2")
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
    
    image_list = cfg.image_ids

    while True:
        for ad in cfg.availability_domains:
            retry_count += 1
            j_count += 1
            
            current_image = image_list[(retry_count - 1) % len(image_list)]

            if j_count >= 10:
                j_count = 0
                notifier.update_status(engine.cloud_name, engine.email, retry_count)

            try:
                public_ip = engine.launch_instance(ad, current_image)
                logging.info(f"🎉 SUCCESS! Created '{cfg.display_name}' in {ad}! IP: {public_ip}")
                notifier.send_success_alert(
                    cloud_name=engine.cloud_name,
                    display_name=cfg.display_name,
                    public_ip=public_ip or "N/A",
                    total_retries=retry_count
                )
                sys.exit(0)

            except oci.exceptions.ServiceError as err:
                err_msg_lower = (err.message or "").lower()
                err_code_lower = (err.code or "").lower()
                is_capacity_error = (
                    "out of host capacity" in err_msg_lower or 
                    "outofcapacity" in err_code_lower or 
                    "capacity" in err_msg_lower
                )

                # 1. Fatal errors (Bad Parameter, Invalid Auth, Unauthorized, Bad Subnet/Image) -> Stop script
                if err.status in (400, 401, 403, 404) or "invalidparameter" in err_code_lower:
                    logging.critical(
                        f"FATAL OCI ERROR {err.status} [{err.code}]: {err.message}. "
                        f"Stopping script immediately to prevent continuous failure."
                    )
                    if notifier.is_enabled():
                        try:
                            notifier.bot.send_message(
                                notifier.uid,
                                f"❌ *OCI Grabber Stopped due to Fatal Error*\n\n"
                                f"Status: `{err.status}` [{err.code}]\n"
                                f"Message: `{err.message}`",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                    # Return exit code 0 on fatal stop so Systemd with Restart=on-failure will NOT continuously restart on fatal bad config
                    sys.exit(0)

                # 2. Rate Limited (429) -> Increase backoff time FIRST, then calculate sleep duration
                elif err.status == 429:
                    wait_time = min(wait_time + 3, 60)
                    jitter = random.uniform(2, 8)
                    sleep_duration = wait_time + jitter
                    logging.info(
                        f"Attempt #{retry_count} [{ad}] - Rate Limited (429): {err.message} "
                        f"| Backoff Sleep: {sleep_duration:.1f}s"
                    )

                # 3. Explicit Capacity Error -> Reset wait_time to minimum interval + jitter
                elif is_capacity_error:
                    wait_time = cfg.minimum_time_interval
                    jitter = random.uniform(2, 8)
                    sleep_duration = wait_time + jitter
                    logging.info(
                        f"Attempt #{retry_count} [{ad}] - Out of Capacity: {err.message} "
                        f"| Retrying in {sleep_duration:.1f}s"
                    )

                # 4. Other 5xx or transient errors -> Retain wait_time + jitter
                else:
                    jitter = random.uniform(2, 8)
                    sleep_duration = wait_time + jitter
                    logging.warning(
                        f"Attempt #{retry_count} [{ad}] - Transient OCI Error {err.status} [{err.code}]: {err.message} "
                        f"| Retrying in {sleep_duration:.1f}s"
                    )
                
                time.sleep(sleep_duration)

            except Exception as ex:
                jitter = random.uniform(2, 8)
                sleep_duration = wait_time + jitter
                logging.error(f"Attempt #{retry_count} [{ad}] - Unexpected Error: {ex} | Retrying in {sleep_duration:.1f}s")
                time.sleep(sleep_duration)

            except KeyboardInterrupt:
                logging.info("Grabber process manually stopped by user. Exiting.")
                sys.exit(0)

if __name__ == "__main__":
    main()
