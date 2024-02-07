# geocat.ch validity checker
![Static Badge](https://img.shields.io/badge/Python-3.9%2B-%2334eb77)

The service uses SMTP server w/o credentials (username & password) to send email. It is intended to use the SMTP from Bund from a server with granted access to the SMTP.  

The validity checker checks the validity of all harvested metadata. The latter is done in 3 steps :

* Run a validation request against metadata to save the validation status within the metadata
* Retrieve the validation status from the metadata's index
* Reset the validation status to leave the metadata as it was before

If metadata are found to be invalid, an email is sent to the metadata owner with a list of invalid metadata.

## Installation
Clone the repo and install dependencies in a python virtual environment (recommended)
```
git clone https://github.com/geoadmin/service-geocat-validity-checker

cd service-geocat-validity-checker

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### at swisstopo (using powershell)
```
git clone https://github.com/geoadmin/service-geocat-validity-checker

cd service-geocat-validity-checker

& "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts\pip3" install --trusted-host github.com --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --proxy=proxy-bvcol.admin.ch:8080 -r requirements.txt
```

## SMTP Mail Server Hostname
You can pass SMTP hostname in environment variables in a `.env` file
```bash
SMTP_ENDPOINT=foo
```
## Login geocat.ch
Since the validity checker fetches information about geocat.ch users (id, email adress), it needs login credentials with administrator profile. The credentials can be pass in a `.env` file :
```bash
GEOCAT_USERNAME=foo
GEOCAT_PASSWORD=foo
```