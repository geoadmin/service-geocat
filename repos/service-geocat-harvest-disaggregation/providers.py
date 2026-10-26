import logging
import json
import os
import hashlib
import config
from sftp_handler import SFTPHandler

logger = logging.getLogger(__name__)

class ProviderManager:
    def __init__(self):
        self.providers = {}
        self.provider_count = {"viageo": 0, "sitg": 0}

    @staticmethod
    def generate_group_id(slug: str) -> int:
        """Generate unique group ID from slug using MD5 hash"""
        hash_value = int(hashlib.md5(slug.encode()).hexdigest(), 16)
        group_id = 50000000 + (hash_value % 10000000)
        return group_id

    def load_viageo_providers(self, geocat_client):
        """Load providers from Viageo API"""
        logger.info("Fetching providers from Viageo")
        try:
            response = geocat_client.session.get(config.VIAGEO_API_URL)
            response.raise_for_status()
            providers = response.json()
            
            for provider in providers:
                uuid = provider.get("uuid")
                slug = provider.get("slug")
                
                if not uuid or not slug:
                    logger.warning(f"Provider missing uuid or slug: {provider}")
                    continue
                
                group_id = self.generate_group_id(slug)
                
                self.providers[uuid] = {
                    "uuid": uuid,
                    "id": provider.get("id"),
                    "group_id": group_id,
                    "name": provider.get("name"),
                    "slug": slug,
                    "group_slug": slug,
                    "group_name": provider.get("name"),
                    "websiteUrl": provider.get("websiteUrl", ""),
                    "logoUrl": provider.get("logoUrl", ""),
                    "logo_filename": f"{slug}.png",
                    "source": "viageo",
                    "email": "",
                    "directory": f"{config.S3_BUCKET_HARVESTING_VIAGEO}/prod/byorg/{uuid}",
                    "beforeScript": "/mnt/geonetwork_data/data/s3sync-geocat-folders.sh asit-geocat-ch"
                }
                self.provider_count["viageo"] += 1
            
            logger.info(f"{self.provider_count['viageo']} providers retrieved from Viageo")
            
        except Exception as e:
            logger.error(f"Error fetching Viageo providers: {e}")

    def load_sitg_providers(self):
        """Load providers from SITG JSON (already downloaded by main.py)"""
        logger.info("Loading providers from SITG JSON file")
        try:
            local_path = "./providers/organisations_sitg.json"

            with open(local_path, "r", encoding="utf-8") as file:
                data = json.load(file)

                for org in data.get("organisations", []):
                    uuid = org.get("uuid")
                    slug = org.get("slug")
                    
                    if not uuid or not slug:
                        logger.warning(f"Organisation missing uuid or slug: {org}")
                        continue
                    
                    is_departement = slug.startswith("departement")
                    group_slug = "canton-de-geneve" if is_departement else slug
                    group_name = "Canton de Genève" if is_departement else org.get("name")
                    group_id = self.generate_group_id(group_slug)

                    if config.GEOCAT_ENV == "int":
                        directory = f"{config.S3_BUCKET_HARVESTING_SITG}/rec/byorg/{uuid}"
                    else:
                        directory = f"{config.S3_BUCKET_HARVESTING_SITG}/prod/byorg/{uuid}"

                    self.providers[uuid] = {
                        "uuid": uuid,
                        "id": self.generate_group_id(slug),
                        "group_id": group_id,
                        "name": org.get("name"),
                        "slug": slug,
                        "group_slug": group_slug,
                        "group_name": group_name,
                        "websiteUrl": org.get("websiteUrl", ""),
                        "logoUrl": org.get("logoUrl", ""),
                        "logo_filename": f"{slug}.png",
                        "source": "sitg",
                        "email": "markus.kesseler@etat.ge.ch",
                        "directory": directory,
                        "beforeScript": "/mnt/geonetwork_data/data/s3sync-geocat-folders.sh ge-geocat-ch"
                    }
                    self.provider_count["sitg"] += 1

            logger.info(f"{self.provider_count['sitg']} providers retrieved from SITG")
            
        except FileNotFoundError:
            logger.error(f"SITG JSON file not found: {local_path}")
            logger.error("Make sure download_organisation_json() was called first")
        except Exception as e:
            logger.error(f"Error loading SITG providers: {e}")

    def get_all_providers(self):
        """Return all loaded providers"""
        return self.providers
