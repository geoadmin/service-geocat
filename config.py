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
            "MD_LegalConstraintsOtherConstraintsObject",
            "contact",
            "contactForResource",
            "contactForDistribution",
            "link"
        ]
    },
    "track_total_hits": True,
    "sort": {"uuid": "asc"},
    "size": 3000
}

MAIL_SENDER = "geocat@swisstopo.ch"

# Mail backend: "outlook" (uses local Outlook COM, no password needed)
#              "smtp"    (uses SMTP server defined in .env)
MAIL_BACKEND = "outlook"

MAIL_SUBJECT = "geocat.ch - Invalid URL in your metadata"

MAIL_BODY_START_TEXT = """
Hello {{name}},

You are receiving this email because you are owner of metadata with invalid URL in the swiss geodata catalogue geocat.ch.

While accessing the following URL, we found some unexpected behaviour.
Please check if those URL are still available and fix them if necessary.

PS: HTTPS or HTTP schema is mandatory for all URL in geocat.ch.

Thank you for your collaboration.
The geocat.ch team

----------

"""

MAIL_BODY_START_HTML = """
<html>
  <body>
    <p>Hello {{name}}<br><br>
        You are receiving this email because you are owner of metadata with invalid URL in the swiss geodata catalogue <a href='https://www.geocat.ch/'>geocat.ch</a>.<br><br>
        While accessing the following URL, we found some unexpected behaviour.<br>
        Please check if those URL are still available and fix them if necessary.<br><br>
        PS: HTTPS or HTTP schema is mandatory for all URL in geocat.ch.<br><br>
       Thank you for your collaboration.<br>
       The geocat.ch team<br><br>
       ----------<br><br>
"""

URL_WHITE_LIST = [
    "^https://map.georessourcen.ethz.ch/$",
    "^https://oereb.llv.li/$",
    "^https://mapplus01/mapplus/.*",
    "^http://sparcgis01.ad.net.fr.ch/.*",
    "^https://sparcgis01.ad.net.fr.ch/.*"
]