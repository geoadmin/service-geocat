from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import geopycat
import config
import copy
import logging
from smtplib import SMTP
import ssl
import os

logger = logging.getLogger(__name__)

def _wait_for_connectivity(check_host: str = "8.8.8.8", interval: int = 30) -> None:
    """Block until internet connectivity is restored, checking every `interval` seconds."""
    import socket
    first = True
    while True:
        try:
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((check_host, 53))
            if not first:
                logger.info("Internet connectivity restored, resuming...")
            return
        except OSError:
            if first:
                logger.warning("Internet connectivity lost. Waiting for connection to be restored (checking every %ss)...", interval)
                first = False
            time.sleep(interval)



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
    for attempt in range(2):
        try:
            geocat.validate_external_metadata(uuid)
            break
        except Exception:
            if attempt == 0:
                logger.warning("Validation failed for %s — waiting for connectivity and retrying...", uuid)
                _wait_for_connectivity()
            else:
                logger.exception("metadata processed : %s - Validation process failed", uuid)
                return

    # --- Checking validity --- #
    query = geopycat.utils.get_search_query(
        q=f'uuid:{uuid}'
    )

    body = copy.deepcopy(config.SEARCH_API_BODY)
    body["query"] = query

    for attempt in range(2):
        try:
            validity = geocat.es_deep_search(body=body)
            break
        except Exception:
            if attempt == 0:
                logger.warning("ES search failed for %s — waiting for connectivity and retrying...", uuid)
                _wait_for_connectivity()
            else:
                logger.exception("metadata processed : %s - Checking validity failed", uuid)
                return

    # --- Reseting validity status --- #
    for attempt in range(2):
        try:
            geocat.reset_validation_status(uuid)
            break
        except Exception:
            if attempt == 0:
                logger.warning("Reset validation status failed for %s — waiting for connectivity and retrying...", uuid)
                _wait_for_connectivity()
            else:
                logger.exception("metadata processed : %s - Reseting validation status failed", uuid)

    if not validity:
        logger.warning("metadata processed : %s - No validity data returned (skipping)", uuid)
        return None

    if validity[0]["_source"]["valid"] == "0":
        return False
    else:
        return True


def get_message(invalid_metadata: list, receiver: str, user_name: str, all_partners: bool = False) -> object:
    """Creates an email message object

    If `all_partners` is True, use the alternate mail-start texts defined in
    `config.MAIL_BODY_START_TEXT_ALL` / `MAIL_BODY_START_HTML_ALL`.
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = config.MAIL_SUBJECT
    message["From"] = config.MAIL_SENDER
    message["To"] = receiver
    message["X-Priority"] = "1"  # 1 (High), 3 (normal), 5 (Low)

    if all_partners:
        start_text = getattr(config, "MAIL_BODY_START_TEXT_ALL", config.MAIL_BODY_START_TEXT)
        start_html = getattr(config, "MAIL_BODY_START_HTML_ALL", config.MAIL_BODY_START_HTML)
    else:
        start_text = config.MAIL_BODY_START_TEXT
        start_html = config.MAIL_BODY_START_HTML

    body_text = start_text.replace("{{name}}", user_name)
    body_html = start_html.replace("{{name}}", user_name)

    for metadata in invalid_metadata:

        body_text += f"Dataset: {config.URL_METADATA}{metadata['uuid']}\n"
        body_html += f"Dataset: <a href='{config.URL_METADATA}{metadata['uuid']}'>{metadata['title']}</a><br>"

    body_html += "</p></body></html>"

    part1 = MIMEText(body_text, "plain")
    part2 = MIMEText(body_html, "html")

    message.attach(part1)
    message.attach(part2)

    return message

def send_email(receivers: list, message: object) -> None:
    """Send an email to the list of receivers using the backend defined in config.MAIL_BACKEND"""

    if config.MAIL_BACKEND == "outlook":
        import win32com.client
        # Extract HTML body from MIMEMultipart object
        html_body = ""
        for part in message.walk():
            if part.get_content_type() == "text/html":
                html_body = part.get_payload(decode=True).decode("utf-8")
                break
        outlook = win32com.client.Dispatch("Outlook.Application")
        for receiver in receivers:
            mail = outlook.CreateItem(0)
            mail.To = receiver
            mail.Subject = message["Subject"]
            mail.HTMLBody = html_body
            mail.SentOnBehalfOfName = config.MAIL_SENDER
            mail.Send()

    elif config.MAIL_BACKEND == "smtp":
        smtp_host = os.environ.get("SMTP_ENDPOINT")
        smtp_port = int(os.environ.get("SMTP_PORT", 25))
        smtp_password = os.environ.get("SMTP_PASSWORD")
        # Ensure network connectivity before attempting SMTP
        _wait_for_connectivity()
        if smtp_password:
            with SMTP("smtp.office365.com", 587) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(config.MAIL_SENDER, smtp_password)
                server.sendmail(config.MAIL_SENDER, receivers, message.as_string())
        else:
            with SMTP(smtp_host, smtp_port) as server:
                server.sendmail(config.MAIL_SENDER, receivers, message.as_string())

    else:
        raise ValueError(f"Unknown MAIL_BACKEND: {config.MAIL_BACKEND}. Use 'outlook' or 'smtp'")
