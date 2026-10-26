# geocat auotomatized upload Script

This project automates the upload of XML and MEF (`.zip`) metadata records to the geocat.ch (GeoNetwork) API.

## Features

- Authenticates to the geocat API using username and password.
- Automatically uploads all `.xml` and `.zip` (MEF) files from a specified folder to the API.
- For MEF files, can validate and/or publish the metadata after upload, depending on parameters.
- Detailed logging of operations and errors.

## Requirements

- Python 3.8+
- A geocat.ch user account with write permissions on the target group.
- Python dependencies:
  - `requests`
  - `python-dotenv` (if you use a `.env` file for credentials)

## Installation

1. **Clone the repository or copy the files into a folder.**

2. **Install dependencies:**
   ```sh
   pip install requests python-dotenv
   ```

3. **Configure parameters in `config.py` and `.env`:**
   - `.env`:
     ```
     GEOCAT_USERNAME=your_username
     GEOCAT_PASSWORD=your_password
     PROXY_HTTP=
     PROXY_HTTPS=
     ```
   - `config.py`: adjust paths, group, and other parameters as needed.

4. **Place your XML and MEF files to upload in the folder defined by `PATH_TO_MD_FILES` in `config.py`.**

## Usage

Simply run:

```sh
python main.py
```

The script will:
- Check if the target folder exists.
- Authenticate the user.
- Upload each `.xml` file as metadata.
- Upload each `.zip` file as MEF, then:
  - **Validate** the metadata if `PARAMETER_VALIDATION` is set to `"True"`.
  - **Publish** the metadata if `PARAMETER_PUBLICATION` is set to `"True"`.

## Automation

### On Linux

Use `cron` to run the script at regular intervals:

```sh
crontab -e
```
Add for example:
```
0 * * * * /usr/bin/python3 /path/to/main.py >> /path/to/cron.log 2>&1
```

### On Windows

Use the **Task Scheduler** to run the script automatically (see Windows documentation).

## Customization

- **Target group**: edit `PARAMETER_GROUP` in `config.py`.
- **Upload parameters**: adjust `PARAMETER_VALIDATION` and `PARAMETER_PUBLICATION` in `config.py` to control MEF validation and publication.
- **Proxy settings**: leave `PROXY_HTTP` and `PROXY_HTTPS` empty if not needed.

## Project Structure

```
.
├── main.py
├── upload_md.py
├── config.py
├── .env
└── [XML/MEF folder]
```

## Logging

Logs are displayed in the console. To redirect them to a file, run:

```sh
python main.py >> log.txt 2>&1
```

## Authors

Script adapted and automated for geocat.ch by swisstopo.

---

**Note:**  
- The script will process all `.xml` and `.zip` files in the target folder.
- For MEF files, validation and publication are controlled by the parameters in `config.py`.
- Make sure your user has the necessary permissions on the target group.
