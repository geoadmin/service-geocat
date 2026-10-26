import os
from dotenv import load_dotenv

load_dotenv()
# Define your environment variables in a .env file
GEOCAT_USERNAME = os.getenv('GEOCAT_USERNAME')
GEOCAT_PASSWORD = os.getenv('GEOCAT_PASSWORD')
PROXY_HTTP = os.getenv('HTTP_PROXY')
PROXY_HTTPS = os.getenv('HTTPS_PROXY')

API_URL = 'https://geocat-int.dev.bgdi.ch/geonetwork/srv/api'
PARAMETER_UUID_PROCESSING = 'OVERWRITE'
PARAMETER_GROUP = '42'  # Replace with the actual group number
PARAMETER_VALIDATION = 'True'
PARAMETER_PUBLICATION = 'True'
PATH_TO_MD_FILES = os.path.expanduser('/home/cuo/Bureau/test_API')  # Update this path to your MD files
# UPDATE_DATE_STAMP = True  # Default value for the new parameter
