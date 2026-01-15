import os
import logging
import requests
import config
import time

logger = logging.getLogger(__name__)

class LogoManager:
    def __init__(self, session, geocat_base_url, default_logo="viageo_logo_couleur.png"):
        self.session = session
        self.default_logo = default_logo
        self.save_directory = config.LOGOS_DIR
        self.sitg_logo_directory = os.path.join(self.save_directory, "SITG")
        self.viageo_logo_directory = os.path.join(self.save_directory, "viageo")
        self.existing_logos = []
        self.geocat_logos_api_url = f"{geocat_base_url}/geonetwork/srv/api/logos"
        self.provider_logo_mapping = {}

        self.ensure_directory(self.save_directory)
        self.ensure_directory(self.sitg_logo_directory)
        self.ensure_directory(self.viageo_logo_directory)

    def ensure_directory(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def fetch_logos_from_geocat(self):
        logger.info("Fetching the list of available logos from geocat")
        headers = {
            "Accept": "application/json",
            "X-XSRF-TOKEN": self.get_csrf_token(),
        }
        try:
            response = self.session.get(self.geocat_logos_api_url, headers=headers)
            response.raise_for_status()
            self.existing_logos = response.json()
            logger.info(f"{len(self.existing_logos)} logos retrieved from geocat")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching logos from geocat: {e}")
            self.existing_logos = []

    def download_logos_from_viageo(self, viageo_api_url):
        logger.info("Fetching provider information from Viageo")
        try:
            response = self.session.get(viageo_api_url)
            response.raise_for_status()
            providers = response.json()

            for provider in providers:
                logo_url = provider.get("logoUrl")
                provider_id = provider.get("id")
                slug = provider.get("slug")
                
                if logo_url and slug:
                    original_extension = os.path.splitext(logo_url)[1]
                    logo_filename = f"{slug}{original_extension}"
                    save_path = os.path.join(self.viageo_logo_directory, logo_filename)

                    logger.info(f"Téléchargement du logo '{logo_filename}' depuis '{logo_url}' vers '{save_path}'")
                    self.download_logo(logo_url, save_path)
                    self.provider_logo_mapping[provider_id] = logo_filename
                else:
                    logger.warning(f"Slug ou logoUrl manquant pour le provider {provider_id}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching provider information from Viageo: {e}")

    def download_logo(self, logo_url, save_path):
        logo_filename = os.path.basename(save_path)
        
        if os.path.exists(save_path):
            logger.info(f"Logo '{logo_filename}' already exists locally. Download skipped.")
            return

        retries = 3
        for i in range(retries):
            logger.info(f"Downloading logo '{logo_filename}' to '{save_path}' (attempt {i + 1}/{retries})")
            try:
                response = self.session.get(logo_url, stream=True, timeout=15)
                response.raise_for_status()
                with open(save_path, 'wb') as logo_file:
                    for chunk in response.iter_content(1024):
                        logo_file.write(chunk)
                logger.info(f"Logo '{logo_filename}' downloaded successfully to '{save_path}'")
                return
            except requests.exceptions.RequestException as e:
                logger.error(f"Error downloading logo from '{logo_url}': {e}")
                if i < retries - 1:
                    logger.info("Retrying after a 5-second delay...")
                    time.sleep(5)

        logger.error(f"Failed to download logo '{logo_filename}' after {retries} attempts.")

    def upload_all_logos(self):
        logger.info("Starting logo uploads to geocat")
        for logo_directory in [self.sitg_logo_directory, self.viageo_logo_directory]:
            for logo_file in os.listdir(logo_directory):
                logo_path = os.path.join(logo_directory, logo_file)
                if os.path.isfile(logo_path):
                    if logo_file not in self.existing_logos:
                        self.upload_logo(logo_path)
                    else:
                        logger.info(f"Logo '{logo_file}' already exists in geocat. Upload skipped.")

    def upload_logo(self, logo_path):
        logo_filename = os.path.basename(logo_path)
        logger.info(f"Uploading logo '{logo_filename}' to geocat from path '{logo_path}'")

        with open(logo_path, 'rb') as logo_file:
            files = {'file': (logo_filename, logo_file, 'image/png')}
            headers = {
                "X-XSRF-TOKEN": self.get_csrf_token(),
                "Accept": "application/json"
            }
            try:
                response = self.session.post(f"{self.geocat_logos_api_url}?overwrite=true", files=files, headers=headers)
                response.raise_for_status()
                logger.info(f"Logo '{logo_filename}' successfully uploaded to geocat.")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error uploading logo '{logo_filename}' to geocat: {e}")
                
    def get_default_logo(self, provider_type):
        if provider_type == "viageo":
            return "default_logo_viageo.png"
        elif provider_type == "sitg":
            return "default_logo_sitg.png"
        return "default_logo.png"

    def get_csrf_token(self):
        token = self.session.cookies.get("XSRF-TOKEN")
        if not token:
            logger.error("Error: Missing XSRF-TOKEN. Authentication may have failed.")
        return token
