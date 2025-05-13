import logging
from urllib.parse import urlparse
import os
from providers import ProviderManager

logger = logging.getLogger(__name__)

class GroupSynchronizer:
    def __init__(self, geocat_client, user_ids=None,logo_manager=None):
        self.geocat_client = geocat_client
        self.providers = {}
        self.geocat_groups = {}
        self.deleted_group_ids = []
        self.added_group_ids = set()
        self.provider_to_geocat_group_ids = {}
        self.user_ids = user_ids or {}
        self.logo_manager = logo_manager

        # Charger les providers via le ProviderManager
        provider_manager = ProviderManager()
        provider_manager.load_viageo_providers(geocat_client)
        provider_manager.load_sitg_providers(os.getenv("S3_BUCKET_SITG_PATH"))
        self.providers = provider_manager.get_all_providers()

    def fetch_geocat_groups(self):
        logger.info("Fetching groups from geocat")
        try:
            groups_url = f"{self.geocat_client.env}/geonetwork/srv/api/groups"
            headers = {"accept": "application/json", "Content-Type": "application/json"}
            response = self.geocat_client.session.get(groups_url, headers=headers)
            response.raise_for_status()
            groups = response.json()
            self.geocat_groups = {group["id"]: group for group in groups}
            logger.info(f"{len(self.geocat_groups)} groups retrieved from geocat")

        except Exception as e:
            logger.error(f"Error fetching geocat groups: {e}")

    def sync_groups(self):
        logger.info("Starting group synchronization process")
        try:
            provider_ids = set(self.providers.keys())
            geocat_provider_groups = {group_id: group for group_id, group in self.geocat_groups.items()
                                      if group.get('owneruser') == 'viageo.ch' or group.get('owneruser') == 'sitg.ch'}
            geocat_provider_ids = set(geocat_provider_groups.keys())

            groups_to_delete = geocat_provider_ids - provider_ids
            groups_to_add = provider_ids - geocat_provider_ids
            groups_to_update = provider_ids & geocat_provider_ids

            for group_id in groups_to_delete:
                self.delete_geocat_group(group_id)
                self.deleted_group_ids.append(group_id)

            for group_id in groups_to_add:
                self.add_geocat_group(self.providers[group_id])
                self.added_group_ids.add(group_id)

            for group_id in groups_to_update:
                self.update_geocat_group_if_needed(group_id)
            
            self.fetch_geocat_groups()
        except Exception as e:
            logger.error(f"Error during group synchronization: {e}")

    def add_geocat_group(self, provider):
        try:
            expected_logo_name = provider.get("logoUrl")
            logo_field = expected_logo_name if expected_logo_name else self.logo_manager.get_default_logo(provider["source"])            
            group_id = provider.get("group_id", provider["id"])
            group_slug = provider.get("group_slug", provider["slug"])
            group_name = provider.get("group_name", provider["name"])

            group_data = {
                "logo": logo_field,
                "website": provider.get("websiteUrl", ""),
                "defaultCategory": None,
                "allowedCategories": [],
                "enableAllowedCategories": False,
                "id": group_id,
                "email": provider["email"],
                "referrer": None,
                "description": None,
                "name": group_slug,
                "label": {lang: group_name for lang in ["eng", "fre", "ger", "ita", "roh"]}
            }

            response = self.geocat_client.session.put(
                f"{self.geocat_client.env}/geonetwork/srv/api/groups",
                headers={"accept": "application/json", "Content-Type": "application/json"},
                json=group_data
            )

            if response.status_code == 201:
                logger.info(f"Group '{provider['slug']}' successfully added with logo '{logo_field}'")
                self.fetch_geocat_groups()
                for group_id, group in self.geocat_groups.items():
                    if group.get("name") == group_slug:
                        provider["group_id"] = group_id
                        self.provider_to_geocat_group_ids[provider["uuid"]] = group_id
                        logger.info(f"Assigned real GeoNetwork group_id {group_id} to provider '{provider['slug']}'")
                        break
            elif response.status_code == 400:
                logger.info(f"Group '{provider['slug']}' already exists.")
                self.fetch_geocat_groups()
                for group_id, group in self.geocat_groups.items():
                    if group.get("name") == group_slug:
                        provider["group_id"] = group_id
                        self.provider_to_geocat_group_ids[provider["uuid"]] = group_id
                        break
            elif response.status_code == 403:
                logger.error(f"Adding group '{provider['slug']}' is not authorized. Only a UserAdmin can add groups.")
            else:
                logger.error(f"Failed to add group '{provider['slug']}': {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Error adding group '{provider['slug']}': {e}")

    def delete_geocat_group(self, group_id):
        group = self.geocat_groups.get(group_id)
        if not group:
            logger.warning(f"Group with ID {group_id} not found in geocat.")
            return

        delete_url = f"{self.geocat_client.env}/geonetwork/srv/api/groups/{group_id}"
        logger.info(f"Deleting group '{group['name']}' (ID: {group_id}) from geocat")

        try:
            response = self.geocat_client.session.delete(delete_url)

            if response.status_code == 204:
                logger.info(f"Group '{group['name']}' successfully deleted")
            elif response.status_code == 403:
                logger.error(f"Deleting group '{group['name']}' is not authorized. Only a UserAdmin can delete groups.")
            else:
                logger.error(f"Failed to delete group '{group['name']}': {response.status_code}, {response.text}")
        except Exception as e:
            logger.error(f"Error deleting group '{group['name']}': {e}")

    def update_geocat_group_if_needed(self, group_id):
        provider = self.providers.get(group_id)
        group = self.geocat_groups.get(group_id)

        if not provider or not group:
            logger.warning(f"Provider or group with ID {group_id} not found.")
            return

        try:
            logo_url = provider.get("logoUrl")
            expected_logo_name = os.path.basename(urlparse(logo_url).path) if logo_url else None
            current_logo_name = group.get("logo", "")
            needs_update = (
                provider["slug"] != group["name"]
                or provider.get("websiteUrl", "") != group.get("website", "")
                or (expected_logo_name and expected_logo_name != current_logo_name)
            )

            if needs_update:
                logo_field = expected_logo_name if expected_logo_name else "default_logo.png"

                update_data = {
                    "id": group_id,
                    "name": provider["slug"],
                    "website": provider.get("websiteUrl", ""),
                    "logo": logo_field,
                    "label": {lang: provider["name"] for lang in ["eng", "fre", "ger", "ita", "roh"]}
                }

                update_url = f"{self.geocat_client.env}/geonetwork/srv/api/groups/{group_id}"
                headers = {"accept": "application/json", "Content-Type": "application/json"}

                response = self.geocat_client.session.put(update_url, headers=headers, json=update_data)

                if response.status_code == 204:
                    logger.info(f"Group '{group['name']}' successfully updated")
                else:
                    logger.error(f"Failed to update group '{group['name']}': {response.status_code}, {response.text}")
            else:
                logger.info(f"No updates needed for group '{group['name']}' (ID: {group_id})")
        except Exception as e:
            logger.error(f"Error updating group '{group['name']}': {e}")
