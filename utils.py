from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import geopycat
import config
import copy
import logging

logger = logging.getLogger(__name__)


def check_md_validity(geocat, uuid: str) -> bool:
    """
    Check the validity of a given metadata

    Performs an internal validation, then fetch metadata index
    to check metadata's validity and finally reset validation status.

    Args:
        geocat : an object of the geopycat geocat class
        uuid : metadata uuid
    """

    # --- Validate metadata --- #
    try:
        geocat.validate_external_metadata(uuid)

    except:
        logger.error("metadata processed : %s - Validation process failed", 
                        uuid)
        return

    # --- Checking validity --- #
    query = geopycat.utils.get_search_query(
        q=f'uuid:{uuid}'
    )

    body = copy.deepcopy(config.SEARCH_API_BODY)
    body["query"] = query

    try:
        validity = geocat.es_deep_search(body=body)

    except:
        logger.error("metadata processed : %s - Checking validity failed", 
                        uuid)
        return

    # --- Reseting validity status --- #
    try:
        geocat.reset_validation_status(uuid)

    except:
        logger.error("metadata processed : %s - Reseting validation status failed", 
                        uuid)

    if validity[0]["_source"]["valid"] == "0":
        return False
    else:
        return True


def get_message(invalid_metadata: list, receiver: str, user_name: str) -> object:
    """Creates an email message object"""

    message = MIMEMultipart("alternative")
    message["Subject"] = config.MAIL_SUBJECT
    message["From"] = config.MAIL_SENDER
    message["To"] = receiver
    message["X-Priority"] = "1"  # 1 (High), 3 (normal), 5 (Low)

    body_text = config.MAIL_BODY_START_TEXT.replace("{{name}}", user_name)
    body_html = config.MAIL_BODY_START_HTML.replace("{{name}}", user_name)

    for metadata in invalid_metadata:

        body_text += f"Dataset: {config.URL_METADATA}{metadata['uuid']}\n"
        body_html += f"Dataset: <a href='{config.URL_METADATA}{metadata['uuid']}'>{metadata['title']}</a><br>"

    body_html += "</p></body></html>"

    part1 = MIMEText(body_text, "plain")
    part2 = MIMEText(body_html, "html")

    message.attach(part1)
    message.attach(part2)

    return message
