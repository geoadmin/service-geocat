import paramiko
import logging
import os

# Configuration du logger
logger = logging.getLogger(__name__)

class SFTPHandler:
    def __init__(self, host, username, private_key_path, port=22):
        self.host = host
        self.username = username
        self.private_key_path = private_key_path
        self.port = port
        self.sftp = None
        self.ssh = None

    def connect(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            key = paramiko.RSAKey(filename=self.private_key_path)
            self.ssh.connect(self.host, port=self.port, username=self.username, pkey=key)
            self.sftp = self.ssh.open_sftp()
            logger.info(f"SFTP connection successful at {self.host}")
        except paramiko.AuthenticationException:
            logger.error(f"SFTP authentication error for user '{self.username}'")
        except paramiko.SSHException as ssh_error:
            logger.error(f"SSH error when connecting to {self.host} : {ssh_error}")
        except Exception as e:
            logger.error(f"SFTP connection error : {e}")

    def download_file(self, remote_path, local_path):
        try:
            if not self.sftp:
                self.connect()

            # Vérifier le chemin distant
            if not remote_path or remote_path == "None":
                logger.error(f"Le chemin distant est invalide : {remote_path}")
                return

            # Vérifier le répertoire distant et son contenu
            remote_dir = os.path.dirname(remote_path)
            logger.info(f"Répertoire distant à vérifier : '{remote_dir}'")
            try:
                files = self.sftp.listdir(remote_dir)
                logger.info(f"Liste des fichiers dans le répertoire '{remote_dir}': {files}")
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du répertoire '{remote_dir}': {e}")
                return

            # Vérifier si le fichier est bien présent
            expected_file = os.path.basename(remote_path)
            logger.info(f"Nom de fichier attendu : '{expected_file}'")

            if expected_file not in files:
                logger.error(f"Le fichier '{expected_file}' n'existe pas dans le répertoire '{remote_dir}'")
                logger.error(f"Fichiers présents : {files}")
                return

            # Créer le répertoire local s'il n'existe pas
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.sftp.get(remote_path, local_path)
            logger.info(f"Téléchargement réussi : {remote_path} -> {local_path}")
        except FileNotFoundError:
            logger.error(f"Fichier distant introuvable : {remote_path}")
        except PermissionError:
            logger.error(f"Permission refusée pour enregistrer le fichier local : {local_path}")
        except Exception as e:
            logger.error(f"Erreur de téléchargement {remote_path} : {e}")

    def close(self):
        try:
            if self.sftp:
                self.sftp.close()
            if self.ssh:
                self.ssh.close()
            logger.info("SFTP connection closed")
        except Exception as e:
            logger.error(f"Error when closing the SFTP connection : {e}")
