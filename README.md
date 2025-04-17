# Geocat Harvester Disaggregation Tool

Python script to synchronize groups, harvesters, and logos between GeoNetwork and external providers (SITG/Viageo).

## Features

- **Group Synchronization**: Creates/updates geocat groups based on SITG/Viageo organizations
- **Harvester Management**: Syncs harvester configurations per organization
- **Logo Handling**: Downloads logos from Viageo and uploads to geocat
- **SFTP Integration**: Fetches configuration files from SFTP server

## Prerequisites

- Python 3.9+
- GeoNetwork (geocat) API access
- SSH key for SFTP (if used)
- Viageo API access (for logos)

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:geoadmin/service-geocat-harvest-disaggregation.git
   cd service-geocat-harvest-disaggregation

    Install dependencies:
    bash
    Copy

    pip install -r requirements.txt

    Configure environment variables (copy .env.example to .env):
    ini
    Copy

    # geocat
    GEOCAT_USER=admin
    GEOCAT_PASSWORD=your_password
    GEOCAT_ENV=prod  # or 'dev'

    # SFTP
    SFTP_HOST=sftp.example.com
    SFTP_USERNAME=user
    SFTP_PRIVATE_KEY_PATH=~/.ssh/id_rsa

    # Viageo
    VIAGEO_API_URL=https://api.viageo.ch/providers

Usage

Run the main script:
bash
Copy

python main.py

Project Structure
Copy
```bash
.
├── main.py               # Main script
├── config.py             # Paths and constants
├── requirements.txt      # Python dependencies
├── .env.example          # Environment template
├── providers/            # Organisation structure
│   └── organisations_provider.json  # Downloaded from SFTP
├── group_sync.py     # Group synchronization
├── harvester_sync.py # Harvester management
├── logo_sync.py      # Logo handling
└── sftp_handler.py   # SFTP operations
```
Key Modules
GroupSynchronizer

    Syncs Geocat groups with source organizations

    Manages UUID → Group ID mappings

    Updates group properties

HarvesterManager

    Creates/removes organization-specific harvesters

    Configures harvester technical parameters

    Manages user permissions

LogoManager

    Downloads logos from Viageo

    Uploads to Geocat with proper filenames

    Handles fallback default logo

SFTPHandler

    Downloads organization JSON from SFTP

    Uses SSH key authentication

Important Notes

    Sensitive Files:

        Never commit .env (included in .gitignore)

        Keep SSH keys private

    Environments:

        Set GEOCAT_ENV to either dev or prod

        S3 paths are configured in config.py

    Logging:

        Logs are saved in ./logs/ with timestamps

        Adjust log level in setup_logging()

License

MIT License - See LICENSE for details.
