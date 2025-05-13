import logging
import os
import config
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring

logger = logging.getLogger(__name__)
def get_harvesting_directory_path(provider):
    if provider.get("source") == "sitg":
        base_path = config.S3_BUCKET_HARVESTING_SITG
    else:
        base_path = config.S3_BUCKET_HARVESTING_VIAGEO
    return f"{base_path}/prod/byorg/{provider['uuid']}"

class HarvesterManager:
    def __init__(self, geocat_client, owner_id, synchronizer):
        self.geocat_client = geocat_client
        self.owner_id = owner_id
        self.harvesters = []
        self.synchronizer = synchronizer

    def fetch_harvesters(self):
        logger.info("Retrieving harvesters from geocat")
        harvester_url = f"{self.geocat_client.env}/geonetwork/srv/eng/admin.harvester.list?_content_type=json"
        response = self.geocat_client.session.get(harvester_url)
        response.raise_for_status()
        self.harvesters = response.json()
        logger.info(f"{len(self.harvesters)} harvesters retrieved")

    def sync_harvesters(self):
        self.fetch_harvesters()

        for group_id in self.synchronizer.added_group_ids:
            provider = self.synchronizer.providers.get(group_id)
            if not provider:
                continue

            if (provider["source"] == "viageo" and self.owner_id != self.synchronizer.user_ids.get(config.VIAGEO_ADMIN)) \
                or (provider["source"] == "sitg" and self.owner_id != self.synchronizer.user_ids.get(config.SITG_ADMIN)):
                continue


            group_name = provider['slug']
            group_logo_url = provider.get('logoUrl')

            if self.harvester_exists_for_group(group_id):
                logger.info(f"Harvester already exists for group '{group_name}' (ID: {group_id})")
            else:
                self.create_harvester_for_group(group_id, group_name, group_logo_url)

    def harvester_exists_for_group(self, group_id):
        provider = self.synchronizer.providers.get(group_id)
        if not provider:
            logger.error(f"Provider avec ID {group_id} introuvable.")
            return False

        directory_path = get_harvesting_directory_path(provider)
        for harvester in self.harvesters:
            if isinstance(harvester, dict):
                harvester_directory = harvester.get('site', {}).get('directory', '')
                if harvester_directory == directory_path:
                    logger.debug(f"Harvesting found : directory_path={directory_path}")
                    return True
        logger.debug(f"No harvesting found for directory_path={directory_path}")
        return False


    def create_harvester_for_group(self, group_id, group_name, group_logo_url):
        try:
            provider = self.synchronizer.providers.get(group_id)
            if not provider:
                logger.error(f"Provider with ID {group_id} not found.")
                return
            
            directory_path = get_harvesting_directory_path(provider)

            # Logo management for provider
            try:
                if group_logo_url:
                    expected_logo_name = os.path.basename(group_logo_url)
                    if self.synchronizer.logo_manager and expected_logo_name in self.synchronizer.logo_manager.existing_logos:
                        icon = expected_logo_name
                    else:
                        icon = "default_logo.png"
                else:
                    icon = "default_logo.png"
            except Exception as e:
                logger.error(f"Error when managing the logo for the group '{group_name}': {e}")
                icon = "default_logo.png"

            # Harvesting name
            try:
                harvester_name = provider["slug"]
                directory_path = provider["directory"]
                before_script = provider["beforeScript"]

                node = Element("node", id="", type="filesystem")
                ownerGroup = SubElement(node, "ownerGroup")
                SubElement(ownerGroup, "id").text = str(provider["group_id"])

                ownerUser = SubElement(node, "ownerUser")
                SubElement(ownerUser, "id").text = str(self.owner_id)

                site = SubElement(node, "site")
                SubElement(site, "name").text = harvester_name
                SubElement(site, "recurse").text = "true"
                SubElement(site, "nodelete").text = "false"
                SubElement(site, "checkFileLastModifiedForUpdate").text = "true"
                SubElement(site, "directory").text = directory_path
                SubElement(site, "recordType").text = "Metadata"
                SubElement(site, "icon").text = icon
                SubElement(site, "beforeScript").text = before_script

                options = SubElement(node, "options")
                SubElement(options, "oneRunOnly").text = "false"
                SubElement(options, "overrideUuid").text = "OVERRIDE"
                SubElement(options, "every").text = "0 0 5 * * ?"
                SubElement(options, "status").text = "active"

                content = SubElement(node, "content")
                SubElement(content, "validate").text = "NOVALIDATION"
                SubElement(content, "importxslt").text = "none"
                SubElement(content, "batchEdits").text = "<![CDATA[[]]]>"

                privileges = SubElement(node, "privileges")
                group_privilege = SubElement(privileges, "group", id="1")
                SubElement(group_privilege, "operation", name="view")
                SubElement(group_privilege, "operation", name="dynamic")
                SubElement(group_privilege, "operation", name="download")

                categories = SubElement(node, "categories")
                SubElement(categories, "category", id="")

                SubElement(node, "ifRecordExistAppendPrivileges").text = "false"
            except Exception as e:
                logger.error(f"Erreur lors de la création du noeud XML pour le moissonneur '{harvester_name}': {e}")
                return

            # Envoi du moissonneur à GeoCat
            try:
                harvester_xml_data = tostring(node, encoding="unicode")
                harvester_url = f"{self.geocat_client.env}/geonetwork/srv/eng/admin.harvester.add?_content_type=json"
                headers = {
                    "Content-Type": "application/xml",
                    "Accept": "application/json",
                    "X-XSRF-TOKEN": self.geocat_client.session.cookies.get("XSRF-TOKEN"),
                }

                response = self.geocat_client.session.post(harvester_url, headers=headers, data=harvester_xml_data)

                if response.status_code == 200:
                    harvester_data = response.json()
                    if isinstance(harvester_data, list) and harvester_data:
                        harvester_id = harvester_data[0]
                        logger.info(f"Harvester for group '{harvester_name}' successfully created with ID {harvester_id}.")                        
                        self.start_harvester(harvester_id)
                    else:
                        logger.error(f"Unexpected response format for harvester '{harvester_name}': {harvester_data}")
                else:
                    logger.error(f"Failed to create harvester for group '{harvester_name}': {response.status_code}, {response.text}")
            except Exception as e:
                logger.error(f"Error when creating the harvester '{harvester_name}': {e}")
        except Exception as e:
            logger.error(f"General error in the creation of the harvester for the group '{group_name}': {e}")


    def start_harvester(self, harvester_id):
        start_url = f"{self.geocat_client.env}/geonetwork/srv/eng/admin.harvester.start?_content_type=json&id={harvester_id}"
        start_response = self.geocat_client.session.get(start_url)

        if start_response.status_code == 200:
            logger.info(f"Harvester ID {harvester_id} successfully activated.")
        else:
            logger.error(f"Failed to activate harvester ID {harvester_id}: {start_response.status_code}, {start_response.text}")
            return

        run_url = f"{self.geocat_client.env}/geonetwork/srv/eng/admin.harvester.run?_content_type=json&id={harvester_id}"
        run_response = self.geocat_client.session.get(run_url)

        if run_response.status_code == 200:
            logger.info(f"Harvester ID {harvester_id} successfully started (run initiated).")
        else:
            logger.error(f"Failed to start harvester ID {harvester_id}: {run_response.status_code}, {run_response.text}")         


    def delete_harvester_for_group(self, viageo_group_id):
        provider = self.synchronizer.viageo_providers.get(viageo_group_id)
        if not provider:
            logger.error(f"Provider with ID {viageo_group_id} not found.")
            return
        viageo_group_uuid = provider.get('uuid')

        directory_path = f"/mnt/s3/asit-geocat-ch/{config.GEOCAT_ENV}/byorg/{viageo_group_uuid}"
        for harvester in self.harvesters:
            if isinstance(harvester, dict):
                harvester_directory = harvester.get('site', {}).get('directory', '')
                if harvester_directory == directory_path:
                    harvester_id = harvester['id']
                    harvester_name = harvester['site'].get('name', '')
                    delete_url = f"{self.geocat_client.env}/geonetwork/srv/eng/admin.harvester.remove"
                    params = {
                        "_content_type": "json",
                        "id": harvester_id
                    }

                    response = self.geocat_client.session.get(delete_url, params=params)
                    if response.status_code == 200:
                        logger.info(f"Harvester '{harvester_name}' (ID: {harvester_id}) successfully deleted.")
                        self.harvesters.remove(harvester)
                    else:
                        logger.error(f"Failed to delete harvester '{harvester_name}': {response.status_code}, {response.text}")
                    break
        else:
            logger.warning(f"No harvester found for group with ID {viageo_group_id}.")
