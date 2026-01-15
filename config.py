import os
from dotenv import load_dotenv

load_dotenv()

# Remote sources for organisations
VIAGEO_API_URL = "https://viageo.ch/api/catalog/provider-list/"
S3_BUCKET_SITG_PATH = os.getenv("S3_BUCKET_SITG_PATH","/ge-geocat-ch/int")

# API geocat
GEOCAT_ENV = os.getenv("GEOCAT_ENV", "int")
GEOCAT_BASE_URL = os.getenv("GEOCAT_BASE_URL", "https://www.geocat.ch")

# Authentification for geocat
GEOCAT_USERNAME = os.getenv("GEOCAT_USERNAME")
GEOCAT_PASSWORD = os.getenv("GEOCAT_PASSWORD")

# Logs folder
LOGS_DIR = os.getenv("LOGS_DIR", "logs")

# Logos folder
LOGOS_DIR = os.getenv("LOGOS_DIR", "logos") 

# SFTP parameters
SFTP_HOST = os.getenv("SFTP_HOST", "sftp.example.com")
SFTP_USERNAME = os.getenv("SFTP_USERNAME", "user")
SFTP_PRIVATE_KEY_PATH = os.getenv("SFTP_PRIVATE_KEY_PATH", "C:/Users/me/private_key_SSH")

#admin user
VIAGEO_ADMIN = "viageo.ch"
SITG_ADMIN = "admin_SITG"

# Config Harvesting path
S3_BUCKET_HARVESTING_VIAGEO = "/mnt/s3/asit-geocat-ch"
S3_BUCKET_HARVESTING_SITG = "/mnt/s3/ge-geocat-ch"