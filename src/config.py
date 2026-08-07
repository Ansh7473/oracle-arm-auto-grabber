from dataclasses import dataclass
import os
from typing import List, Optional
from dotenv import load_dotenv

@dataclass
class Config:
    availability_domains: List[str]
    display_name: str
    compartment_id: str
    subnet_id: str
    ssh_authorized_keys: str
    image_ids: List[str]
    boot_volume_size_in_gbs: int
    ocpus: int
    memory_in_gbs: int
    minimum_time_interval: int
    max_allowed_ocpus: int
    max_allowed_memory_gb: int
    bot_token: Optional[str]
    uid: Optional[str]
    oci_config_file: str

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "Config":
        if env_path and os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            load_dotenv()

        ads_raw = os.getenv("AVAILABILITY_DOMAINS", "")
        ads = [ad.strip() for ad in ads_raw.split(",") if ad.strip()]

        display_name = os.getenv("DISPLAY_NAME", "instance-arm-node")
        compartment_id = os.getenv("COMPARTMENT_ID", "")
        subnet_id = os.getenv("SUBNET_ID", "")
        ssh_keys = os.getenv("SSH_AUTHORIZED_KEYS", "")
        
        image_ids_raw = os.getenv("IMAGE_ID", "")
        image_ids = [img.strip() for img in image_ids_raw.split(",") if img.strip()]
        
        boot_vol_size = int(os.getenv("BOOT_VOLUME_SIZE_IN_GBS", "100"))
        ocpus = int(os.getenv("OCPUS", "1"))
        memory_gb = int(os.getenv("MEMORY_IN_GBS", "6"))
        min_interval = int(os.getenv("MINIMUM_TIME_INTERVAL", "35"))
        
        max_ocpus = int(os.getenv("MAX_ALLOWED_OCPUS", "2"))
        max_mem = int(os.getenv("MAX_ALLOWED_MEMORY_GB", "12"))

        bot_token = os.getenv("BOT_TOKEN")
        uid = os.getenv("UID")
        
        config_file = os.getenv("OCI_CLI_CONFIG_FILE", os.path.expanduser("~/.oci/config"))

        return cls(
            availability_domains=ads,
            display_name=display_name,
            compartment_id=compartment_id,
            subnet_id=subnet_id,
            ssh_authorized_keys=ssh_keys,
            image_ids=image_ids,
            boot_volume_size_in_gbs=boot_vol_size,
            ocpus=ocpus,
            memory_in_gbs=memory_gb,
            minimum_time_interval=min_interval,
            max_allowed_ocpus=max_ocpus,
            max_allowed_memory_gb=max_mem,
            bot_token=bot_token if bot_token and bot_token != "xxxx" else None,
            uid=uid if uid and uid != "xxxx" else None,
            oci_config_file=config_file
        )
