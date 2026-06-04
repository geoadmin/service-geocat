HOST = "https://www.geocat.ch"

URL_METADATA = f"{HOST}/geonetwork/srv/eng/catalog.search#/metadata/"

SEARCH_API_BODY = {
    "from": 0,
    "query": {
        "bool": {
            "must": []
        }
    },
    "_source": {
        "includes": [
            "uuid",
            "resourceTitleObject",
            "valid"
        ]
    },
    "track_total_hits": True,
    "sort": {"_id": "asc"},
    "size": 3000
}

MAIL_SENDER = "geocat@swisstopo.ch"

# Mail backend: "outlook" (uses local Outlook COM, no password needed)
#              "smtp"    (uses SMTP server defined in .env)
MAIL_BACKEND = "outlook"

# When True, target only partners that are harvesters.
# When False, use the "ALL" mail body and target local partners as well.
HARVESTER_ONLY = False

MAIL_SUBJECT = "geocat.ch - Invalid metadata"

MAIL_BODY_START_TEXT = """
Hello {{name}},

You are receiving this email because you are owner of invalid metadata that are present in the swiss geodata catalogue geocat.ch.
The following metadata were found to be not valid because they don't respect the swiss geographical metadata profile.

To maintain a good quality of the swiss geodata catalog, we ask you to check and correct these metadata so that they comply with the swiss geographical metadata profile.
If you take no action, the invalid metadata may still be harvested and published on geocat.ch.

To help you achieve this goal :

- You can find more information on the swiss geospatial metadata profile and its implementation in XML (eCH-0271 / iso19115-3.2018.che) here : https://www.ech.ch/de/ech/ech-0271/1.0.0
- You can download a commented XML file as an example of a metadata compliant with the profile :
    - French: https://backend.info.geocat.ch/fileservice/sdweb-docs-prod-geocat-files/files/2026/03/19/abf68940-e7a9-49e9-bbd2-864692f88371.xml
    - German: https://backend.info.geocat.ch/fileservice/sdweb-docs-prod-geocat-files/files/2026/03/19/e36cb075-991b-4493-9db4-38984c4ff1ea.xml
- You can validate your metadata using the swiss geometa validator (hosted): https://web-swiss-geometa-validator.onrender.com/

Thank you for your collaboration.
The geocat.ch team

----------
Invalid records found :

"""

MAIL_BODY_START_HTML = """
<html>
    <body>
        <p>Hello {{name}}<br><br>
                You are receiving this email because you are owner of <b>invalid metadata</b> that are present in the swiss geodata catalogue <a href='https://www.geocat.ch/'>geocat.ch</a>.<br>
                The following metadata were found to be not valid because <b>they don't respect the swiss geographical metadata profile.</b><br><br>
                To maintain a good quality of the swiss geodata catalog, <b>we ask you to check and correct these metadata</b> so that they comply with the swiss geographical metadata profile.<br>
                If you take no action, the invalid metadata may still be harvested and published on geocat.ch.<br><br>
                To help you achieve this goal :
                <ul>
                        <li>You can find more information on the swiss geospatial metadata profile and its implementation in XML (eCH-0271 / iso19115-3.2018.che) <a href='https://www.ech.ch/de/ech/ech-0271/1.0.0'>here</a></li>
                        <li>You can download a commented XML file as an example of a metadata compliant with the profile :
                                <ul>
                                        <li><a href='https://backend.info.geocat.ch/fileservice/sdweb-docs-prod-geocat-files/files/2026/03/19/abf68940-e7a9-49e9-bbd2-864692f88371.xml'>Exemple (FR)</a></li>
                                        <li><a href='https://backend.info.geocat.ch/fileservice/sdweb-docs-prod-geocat-files/files/2026/03/19/e36cb075-991b-4493-9db4-38984c4ff1ea.xml'>Exemple (DE)</a></li>
                                </ul>
                        </li>
                        <li>You can validate your metadata using the swiss geometa validator (hosted): <a href='https://web-swiss-geometa-validator.onrender.com/'>web-swiss-geometa-validator</a></li>
                </ul>
             Thank you for your collaboration.<br>
             The geocat.ch team<br><br>
             ----------<br>
             Invalid records found :
             <br><br>
"""

# Alternate mail body for when targeting ALL partners (not only harvesters)
# Use when you call the script with harvester_only=False / target local partners
MAIL_BODY_START_TEXT_ALL = MAIL_BODY_START_TEXT
MAIL_BODY_START_HTML_ALL = MAIL_BODY_START_HTML