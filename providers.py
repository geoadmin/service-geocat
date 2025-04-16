import logging
import json
import os
import config
from sftp_handler import SFTPHandler

logger = logging.getLogger(__name__)

class ProviderManager:
    def __init__(self):
        self.providers = {}
        self.existing_group_ids = set()


    def generate_group_id(slug: str) -> int:
        return abs(sum(ord(char) for char in slug)) % 1000000

    def load_viageo_providers(self, geocat_client):
        """Uploading providers from the Viageo API"""
        logger.info("Fetching providers from Viageo")
        try:
            response = geocat_client.session.get(config.VIAGEO_API_URL)
            response.raise_for_status()
            providers = response.json()
            
            # Normaliser les données Viageo
            viageo_providers = {}
            for provider in providers:
                viageo_providers[provider["uuid"]] = {
                    "id": provider["id"],
                    "uuid": provider["uuid"],
                    "name": provider["name"],
                    "slug": provider["slug"],
                    "websiteUrl": provider.get("websiteUrl", ""),
                    "logoUrl": provider.get("logoUrl", ""),
                    "source": "viageo",
                    "email": "xavier.merour@asit-asso.ch",
                    "directory": f"{config.S3_BUCKET_HARVESTING_VIAGEO}/{config.GEOCAT_ENV}/byorg/{provider['uuid']}",
                    "beforeScript": "/mnt/geonetwork_data/data/s3sync-geocat-folders.sh asit-geocat-ch"
                }
            self.providers.update(viageo_providers)
            logger.info(f"{len(viageo_providers)} providers retrieved from Viageo")
        except Exception as e:
            logger.error(f"Error fetching Viageo providers: {e}")

    def load_sitg_providers(self, s3_bucket_path):
        logger.info("Fetching providers from SITG (S3 bucket)")
        try:
            local_path = "./providers/organisations_sitg.json"
            remote_path = f"{s3_bucket_path}/organisations.json"

            sftp = SFTPHandler(
                host=os.getenv("SFTP_HOST"),
                username=os.getenv("SFTP_USERNAME"),
                private_key_path=os.getenv("SFTP_PRIVATE_KEY_PATH")
            )
            sftp.connect()
            sftp.download_file(remote_path, local_path)
            sftp.close()

            with open(local_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                sitg_providers = {}

                for org in data.get("organisations", []):
                    is_departement = org["slug"].startswith("departement")

                    group_slug = "canton-de-geneve" if is_departement else org["slug"]
                    group_name = "Canton de Genève" if is_departement else org["name"]
                    group_id = ProviderManager.generate_group_id(group_slug)

                    sitg_providers[org["uuid"]] = {
                        "id": group_id,
                        "uuid": org["uuid"],
                        "name": org["name"],
                        "slug": org["slug"],
                        "websiteUrl": org.get("websiteUrl", ""),
                        "logoUrl": f"{org['uuid']}.png",
                        "source": "sitg",
                        "email": "markus.kesseler@etat.ge.ch",
                        "directory": f"{config.S3_BUCKET_HARVESTING_SITG}/{config.GEOCAT_ENV}/byorg/{org['uuid']}",
                        "beforeScript": "/mnt/geonetwork_data/data/s3sync-geocat-folders.sh ge-geocat-ch",
                        # Groupe GeoCat
                        "group_id": group_id,
                        "group_slug": group_slug,
                        "group_name": group_name
                    }

            self.providers.update(sitg_providers)
            logger.info(f"{len(sitg_providers)} providers retrieved from SITG")
        except Exception as e:
            logger.error(f"Error fetching SITG providers: {e}")

    def get_all_providers(self):
        """Return all loaded providers"""
        return self.providers
