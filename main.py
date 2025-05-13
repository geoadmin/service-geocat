import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import config
import geopycat
from group_sync import GroupSynchronizer
from harvester_sync import HarvesterManager
from logo_sync import LogoManager
from sftp_handler import SFTPHandler

def setup_logging():
    logs_dir = config.LOGS_DIR
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    logfile = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
    log_file_path = os.path.join(logs_dir, logfile)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def get_user_id(geocat, username):
    logger = logging.getLogger(__name__)
    users = geocat.get_users()
    for user in users:
        if user.get("username") == username:
            user_id = user.get("id")
            logger.info(f"User ID for '{username}': {user_id}")
            return user_id
    logger.warning(f"User '{username}' not found.")
    return None


def download_organisation_json():
    sftp = SFTPHandler(
        host=config.SFTP_HOST,
        username=config.SFTP_USERNAME,
        private_key_path=config.SFTP_PRIVATE_KEY_PATH
    )
    sftp.connect()

    # Vérifier la valeur de S3_BUCKET_SITG_PATH
    logging.info(f"S3_BUCKET_PATH depuis la config: '{config.S3_BUCKET_SITG_PATH}'")

    # Vérifier si S3_BUCKET_PATH est vide ou None
    if not config.S3_BUCKET_SITG_PATH:
        logging.error("Le chemin S3_BUCKET_SITG_PATH est vide ou non défini. Vérifiez votre configuration.")
        sftp.close()
        return None

    local_path = "./providers/organisations_sitg.json"
    logging.info(f"Téléchargement depuis '{remote_path}' vers '{local_path}'")

    remote_path = f"{config.S3_BUCKET_SITG_PATH}/organisations.json"
    logging.info(f"Téléchargement du fichier depuis le chemin SFTP : '{remote_path}'")
    

    # Vérifier si le chemin est bien formé
    if not remote_path or remote_path == "None":
        logging.error("Le chemin du fichier SFTP est invalide. Vérifiez la configuration.")
        sftp.close()
        return None

    sftp.download_file(remote_path, local_path)
    sftp.close()
    return local_path


def load_organisation_data():
    json_path = download_organisation_json()
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return {org["uuid"]: org for org in data.get("organisations", [])}
    except Exception as e:
        logging.error(f"Error reading organisation JSON file: {e}")
        return {}

def main():
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Start of the group synchronisation script")
    
    geocat = geopycat.geocat(env=config.GEOCAT_ENV)

    user_ids = {}

    logo_manager = LogoManager(
        session=geocat.session, 
        geocat_base_url=geocat.env,
        default_logo="default_logo.png"
    )
    logo_manager.fetch_logos_from_geocat()
    logo_manager.download_logos_from_viageo(config.VIAGEO_API_URL)
    logo_manager.upload_all_logos()

    # D’abord récupérer les user_ids
    for user_name in [config.VIAGEO_ADMIN, config.SITG_ADMIN]:
        user_id = get_user_id(geocat, user_name)
        if user_id is None:
            logger.error(f"User cannot be found '{user_name}'")
        else:
            user_ids[user_name] = user_id
            logger.info(f"User '{user_name}' found with ID {user_id}")

    if not user_ids:
        logger.error("No valid user found. Script termination.")
        return

    # Ensuite, initialiser le synchronizer
    synchronizer = GroupSynchronizer(geocat, user_ids=user_ids, logo_manager=logo_manager)
    synchronizer.fetch_geocat_groups()
    synchronizer.sync_groups()

    # Puis exécuter les harvesters
    for user_name, user_id in user_ids.items():
        logger.info(f"Start of harvest management for the user '{user_name}'")
        harvester_sync = HarvesterManager(geocat, user_id, synchronizer)
        harvester_sync.sync_harvesters()


if __name__ == "__main__":
    main()


