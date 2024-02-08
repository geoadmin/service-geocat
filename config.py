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

MAIL_SUBJECT = "geocat.ch - Invalid metadata"

MAIL_BODY_START_TEXT = """
Hello {{name}},

You are receiving this email because you are owner of invalid metadata that have been harvested into the swiss geodata catalogue geocat.ch.
The following metadata were found to be not valid because they don't respect the swiss geographical metadata profile.

To maintain a good quality of the swiss geodata catalog, we ask you to check and correct these metadata so that they comply with the swiss geographical metadata profile.
If you take no action, the invalid metadata will still be harvested and published on geocat.ch.

To help you achieve this goal :

- You can find more information on the swiss geospatial metadata profile and its implementation in XML (iso19139.che) here : https://www.geocat.admin.ch/en/documentation/standards.html.
- You can download a commented XML file as an example of a metadata compliant with the iso19139.che profile : https://www.geocat.admin.ch/content/geocat-internet/de/documentation/application/direct/_jcr_content/contentPar/downloadlist_copy/downloadItems/3_1652772838185.download/xml_ISO19139_che_DE.txt
- You can download and install the swiss geometa validator (beta version) to check the validity of your metadata : https://github.com/geoadmin/web-swiss-geometa-validator

Thank you for your collaboration.
The geocat.ch team

----------
Invalid records found :

"""

MAIL_BODY_START_HTML = """
<html>
  <body>
    <p>Hello {{name}}<br><br>
        You are receiving this email because you are owner of <b>invalid metadata</b> that have been harvested into the swiss geodata catalogue <a href='https://www.geocat.ch/'>geocat.ch</a>.<br>
        The following metadata were found to be not valid because <b>they don't respect the swiss geographical metadata profile.</b><br><br>
        To maintain a good quality of the swiss geodata catalog, <b>we ask you to check and correct these metadata</b> so that they comply with the swiss geographical metadata profile.<br>
        If you take no action, the invalid metadata will still be harvested and published on geocat.ch.<br><br>
        To help you achieve this goal :
        <ul>
            <li>You can find more information on the swiss geospatial metadata profile and its implementation in XML (iso19139.che) <a href='https://www.geocat.admin.ch/en/documentation/standards.html'>here</a></li>
            <li>You can download a commented XML file as an example of a metadata compliant with the iso19139.che profile : <a href='https://www.geocat.admin.ch/content/geocat-internet/de/documentation/application/direct/_jcr_content/contentPar/downloadlist_copy/downloadItems/3_1652772838185.download/xml_ISO19139_che_DE.txt'>download</a></li>
            <li>You can download and install the swiss geometa validator (beta version) to check the validity of your metadata : <a href='https://github.com/geoadmin/web-swiss-geometa-validator'>The swiss geometa validator</a></li>
        </ul>
       Thank you for your collaboration.<br>
       The geocat.ch team<br><br>
       ----------<br>
       Invalid records found :
       <br><br>
"""