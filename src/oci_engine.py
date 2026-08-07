import logging
import random
import sys
import time
import uuid
from typing import Optional, List

import oci
from src.config import Config

class OCIEngine:
    def __init__(self, config: Config):
        self.cfg = config
        logging.info("Initializing OCI SDK Clients...")
        self.oci_config = oci.config.from_file(file_location=config.oci_config_file)
        
        self.compute_client = oci.core.ComputeClient(self.oci_config)
        self.identity_client = oci.identity.IdentityClient(self.oci_config)
        self.vcn_client = oci.core.VirtualNetworkClient(self.oci_config)
        self.volume_client = oci.core.BlockstorageClient(self.oci_config)

        try:
            self.cloud_name = self.identity_client.get_tenancy(tenancy_id=config.compartment_id).data.name
        except Exception:
            self.cloud_name = "OCI Account"
            
        try:
            users = self.identity_client.list_users(compartment_id=config.compartment_id).data
            self.email = users[0].email if users else "N/A"
        except Exception:
            self.email = "N/A"

    def run_preflight_checks(self):
        logging.info("Running storage & quota preflight checks...")
        
        if not self.cfg.availability_domains:
            logging.critical("No AVAILABILITY_DOMAINS configured in environment! Stopping.")
            sys.exit(1)

        if not self.cfg.image_ids or self.cfg.image_ids == ["xxxx"]:
            logging.critical("No IMAGE_ID configured in environment! Stopping.")
            sys.exit(1)

        # 1. Storage check
        total_volume_gb = 0
        try:
            volumes = self.volume_client.list_volumes(compartment_id=self.cfg.compartment_id).data
            for v in volumes:
                if v.lifecycle_state not in ("TERMINATING", "TERMINATED"):
                    total_volume_gb += v.size_in_gbs
        except Exception as e:
            logging.error(f"Storage check error: {e}")

        for ad in self.cfg.availability_domains:
            try:
                boot_vols = self.volume_client.list_boot_volumes(
                    availability_domain=ad, compartment_id=self.cfg.compartment_id
                ).data
                for bv in boot_vols:
                    if bv.lifecycle_state not in ("TERMINATING", "TERMINATED"):
                        total_volume_gb += bv.size_in_gbs
            except Exception:
                pass

        free_storage = 200 - total_volume_gb
        if free_storage < self.cfg.boot_volume_size_in_gbs:
            logging.critical(
                f"Storage Precheck Failed: Free storage is {free_storage} GB out of 200 GB limit, "
                f"but target requires {self.cfg.boot_volume_size_in_gbs} GB. Stopping."
            )
            sys.exit(1)

        # 2. Instance & OCPU check
        instances = self.compute_client.list_instances(compartment_id=self.cfg.compartment_id).data
        used_ocpus = 0
        used_memory = 0
        existing_names = []

        if instances:
            for inst in instances:
                existing_names.append(inst.display_name)
                if inst.shape == "VM.Standard.A1.Flex" and inst.lifecycle_state not in ("TERMINATING", "TERMINATED"):
                    used_ocpus += int(inst.shape_config.ocpus)
                    used_memory += int(inst.shape_config.memory_in_gbs)

        logging.info(
            f"Account ARM Usage: {used_ocpus}/4 OCPUs, {used_memory}/24 GB RAM. "
            f"Free Capacity: {4 - used_ocpus} OCPUs, {24 - used_memory} GB RAM."
        )

        if used_ocpus + self.cfg.ocpus > 4 or used_memory + self.cfg.memory_in_gbs > 24:
            logging.critical(
                f"Always-Free ARM Limit Exceeded: Requested {self.cfg.ocpus} OCPU / {self.cfg.memory_in_gbs} GB RAM, "
                f"but account is already using {used_ocpus} OCPU / {used_memory} GB RAM. Stopping."
            )
            sys.exit(1)

        if self.cfg.display_name in existing_names:
            logging.critical(f"Duplicate instance name '{self.cfg.display_name}' already exists. Stopping.")
            sys.exit(1)

        logging.info("Preflight checks passed! Target is fully within Always-Free limits.")

    def launch_instance(self, availability_domain: str, image_id: str, retry_token: Optional[str] = None) -> Optional[str]:
        source_details = oci.core.models.InstanceSourceViaImageDetails(
            source_type="image",
            image_id=image_id,
            boot_volume_size_in_gbs=self.cfg.boot_volume_size_in_gbs
        )

        launch_details = oci.core.models.LaunchInstanceDetails(
            metadata={"ssh_authorized_keys": self.cfg.ssh_authorized_keys},
            availability_domain=availability_domain,
            shape="VM.Standard.A1.Flex",
            compartment_id=self.cfg.compartment_id,
            display_name=self.cfg.display_name,
            is_pv_encryption_in_transit_enabled=True,
            source_details=source_details,
            create_vnic_details=oci.core.models.CreateVnicDetails(
                assign_public_ip=True, subnet_id=self.cfg.subnet_id
            ),
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=self.cfg.ocpus, memory_in_gbs=self.cfg.memory_in_gbs
            )
        )

        # Re-use deterministic retry_token per launch session to guarantee idempotency across network timeouts
        if not retry_token:
            retry_token = str(uuid.uuid4())

        resp = self.compute_client.launch_instance(launch_details, opc_retry_token=retry_token)
        instance_id = resp.data.id

        # Fetch Public IP
        time.sleep(30)
        public_ip = "N/A"
        try:
            vnics = self.compute_client.list_vnic_attachments(
                compartment_id=self.cfg.compartment_id, instance_id=instance_id
            ).data
            if vnics:
                private_ips = self.vcn_client.list_private_ips(
                    subnet_id=self.cfg.subnet_id, vnic_id=vnics[0].vnic_id
                ).data
                if private_ips:
                    pub_ip_obj = self.vcn_client.get_public_ip_by_private_ip_id(
                        oci.core.models.GetPublicIpByPrivateIpIdDetails(private_ip_id=private_ips[0].id)
                    ).data
                    public_ip = pub_ip_obj.ip_address
        except Exception as err:
            logging.warning(f"Could not resolve public IP immediately: {err}")

        return public_ip
