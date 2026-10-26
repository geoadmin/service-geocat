import logging
import os
from urllib.parse import urlparse
from providers import ProviderManager

logger = logging.getLogger(__name__)

class GroupSynchronizer:
    def __init__(self, geocat_client, user_ids=None, logo_manager=None):
        self.geocat_client = geocat_client
        self.geocat_groups = {}
        self.added_group_ids = set()
        self.user_ids = user_ids or {}
        self.logo_manager = logo_manager

        # Charger les providers
        provider_manager = ProviderManager()
        provider_manager.load_viageo_providers(geocat_client)
        provider_manager.load_sitg_providers()
        self.providers = provider_manager.get_all_providers()

    def fetch_geocat_groups(self):
        """Fetch existing groups from GeoCAT"""
        logger.info("Fetching groups from geocat")
        try:
            groups_url = f"{self.geocat_client.env}/geonetwork/srv/api/groups"
            headers = {"accept": "application/json"}
            response = self.geocat_client.session.get(groups_url, headers=headers)
            response.raise_for_status()
            groups = response.json()
            
            self.geocat_groups = {group["name"]: group for group in groups}
            logger.info(f"{len(self.geocat_groups)} groups retrieved from geocat")

        except Exception as e:
            logger.error(f"Error fetching geocat groups: {e}")

    def sync_groups(self):
        """Synchronize groups and track providers"""
        logger.info("Starting group synchronization process")
        
        unique_groups = {}
        for provider_uuid, provider in self.providers.items():
            group_slug = provider.get("group_slug")
            
            if not group_slug:
                logger.warning(f"Provider {provider_uuid} missing group_slug, skipping")
                continue
            
            if group_slug not in unique_groups:
                unique_groups[group_slug] = provider
        
        logger.info(f"Processing {len(unique_groups)} unique groups")
        
        for group_slug, group_provider in unique_groups.items():
            
            if group_slug not in self.geocat_groups:
                # ✅ Créer nouveau groupe
                logger.info(f"Creating new group: {group_slug}")
                created_group_id = self.add_geocat_group(group_provider)
                
                if created_group_id:
                    # ✅ Mettre à jour group_id pour TOUS les providers de ce groupe
                    for prov in self.providers.values():
                        if prov.get("group_slug") == group_slug:
                            prov["group_id"] = created_group_id
            else:
                # ✅ Groupe existe déjà - RÉCUPÉRER le group_id
                existing_group_id = self.geocat_groups[group_slug].get("id")
                logger.info(f"Group '{group_slug}' already exists (ID: {existing_group_id})")
                
                # ✅ IMPORTANT : Mettre à jour group_id pour TOUS les providers de ce groupe
                for prov in self.providers.values():
                    if prov.get("group_slug") == group_slug:
                        prov["group_id"] = existing_group_id
                        logger.debug(f"Updated group_id={existing_group_id} for provider {prov.get('slug')}")
            
            # ✅ Ajouter tous les providers de ce groupe à added_group_ids
            for provider_uuid, provider in self.providers.items():
                if provider.get("group_slug") == group_slug:
                    self.added_group_ids.add(provider_uuid)
        
        logger.info(f"Total providers ready for harvester creation: {len(self.added_group_ids)}")

    def add_geocat_group(self, provider):
        """Create a new group in geocat"""
        group_slug = provider.get("group_slug")
        
        try:
            logo_filename = f"{group_slug}.png"
            if self.logo_manager and logo_filename not in self.logo_manager.existing_logos:
                logo_filename = "default_logo.png"

            group_data = {
                "name": group_slug,
                "description": "",
                "email": provider.get("email", ""),
                "enableAllowedCategories": False,
                "allowedCategories": [],
                "defaultCategory": None,
                "logo": logo_filename,
                "referrer": None,
                "website": provider.get("websiteUrl", ""),
                "label": {
                    "eng": provider.get("group_name"),
                    "fre": provider.get("group_name"),
                    "ger": provider.get("group_name"),
                    "ita": provider.get("group_name"),
                    "roh": provider.get("group_name")
                }
            }

            xsrf_token = self.geocat_client.session.cookies.get("XSRF-TOKEN")
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "X-XSRF-TOKEN": xsrf_token
            }

            response = self.geocat_client.session.put(
                f"{self.geocat_client.env}/geonetwork/srv/api/groups",
                headers=headers,
                json=group_data
            )

            if response.status_code == 201:
                group_id = response.json()
                logger.info(f"✅ Group '{group_slug}' successfully created with ID {group_id}")
                
                self.geocat_groups[group_slug] = {"id": group_id, "name": group_slug}
                
                return group_id
                
            elif response.status_code == 400:
                logger.warning(f"Group '{group_slug}' may already exist: {response.text}")
                self.fetch_geocat_groups()
                if group_slug in self.geocat_groups:
                    group_id = self.geocat_groups[group_slug]["id"]
                    logger.info(f"Retrieved existing group_id={group_id} for '{group_slug}'")
                    return group_id
                return None
            else:
                logger.error(f"Failed to create group '{group_slug}': {response.status_code}, {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating group '{group_slug}': {e}")
            return None
