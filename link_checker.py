from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http import HTTPStatus
import time
import re
import requests
import config
import logging
from smtplib import SMTP
import ssl
import os

logger = logging.getLogger(__name__)

def __url_checker(url: str, allow_redirects: bool = True) -> bool:
    """Check if URL is valid"""
    
    if not url or not url.strip():
        logger.error("Invalid URL: Empty or whitespace-only URL detected.")
        return False

    if ' ' in url:
        from urllib.parse import quote
        encoded_url = quote(url, safe=':/?#[]@!$&\'()*+,;=%')
        logger.warning("URL contains spaces, testing encoded version: %s -> %s", url, encoded_url)
        return __url_checker(encoded_url, allow_redirects)

    if url.startswith('local://'):
        logger.info(f"Ignoring local URL: {url}")
        return True

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76"
    }

    RETRY = 5

    RETRY_CODE = [
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    ]

    PASS_CODE = [
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    ]

    for url_in_white_list in config.URL_WHITE_LIST:
        if re.search(url_in_white_list, url):
            return True
    
    logger.info(f"Checking URL: {url}")

    for i in range(RETRY):
        try:
            with requests.get(url=url, allow_redirects=allow_redirects, timeout=30, headers=headers, stream=True, verify=False) as response:
                response.raise_for_status()

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code
            if code in RETRY_CODE:
                logger.warning("Retrying URL (try %s): %s - %s", i + 1, url, repr(exc))
                time.sleep((i + 1) ** 2)
                continue
            elif code in PASS_CODE:
                return True
            else:
                logger.error("Invalid URL: %s - %s", url, repr(exc))
                return False

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Checking URL (try %s): %s - %s", i + 1, url, repr(exc))
            time.sleep(i ** 2 + 1)
            continue

        except requests.exceptions.RequestException as exc:
            logger.error("Invalid URL: %s - %s", url, repr(exc))
            return False

        else:
            return True

    logger.error("Invalid URL: %s", url)
    return False


def check_metadata_url(index: dict, valid_url: list) -> dict:
    """Check if URL of metadata are valid"""

    result = {
        "uuid": index["_source"]["uuid"], 
        "title": index["_source"].get("resourceTitleObject", {}).get("default", "No title"), 
        "errors": list()        
    }

    new_valid_url = []

    try:
        # 1. Website for contacts (multilingual)
        for contact in ["contact", "contactForResource", "contactForDistribution"]:
            if contact in index["_source"]:
                for i in index["_source"][contact]:
                    if "websiteObject" in i:
                        for lang, website in i["websiteObject"].items():
                            if website not in valid_url and not __url_checker(website):
                                result["errors"].append(
                                    {
                                        "url": website,
                                        "location": f"Website of {contact} in language {lang}"
                                    }
                                )
                            else:
                                new_valid_url.append(website)
                                valid_url.append(website)

        # 2. Resources Link (multilingual)
        if "link" in index["_source"]:
            for i in index["_source"]["link"]:
                for lang, url in i["urlObject"].items():
                    if url not in valid_url and not __url_checker(url, allow_redirects=i["protocol"].startswith(("OGC:WMS", "OGC:WMTS", "OGC:WFS"))):
                        result["errors"].append(
                            {
                                "url": url,
                                "location": f"Online resource URL in language {lang} with {i['protocol']} protocol"
                            }
                        )
                    else:
                        new_valid_url.append(url)
                        valid_url.append(url)

        # 3. Verify links in abstract (multilingual)
        if "resourceAbstractObject" in index["_source"]:
            abstract_data = index["_source"]["resourceAbstractObject"]

            for lang_key, abstract_text in abstract_data.items():
                urls_in_abstract = re.findall(r'http[s]?://\S+', abstract_text)
                for url in urls_in_abstract:
                    if url not in valid_url and not __url_checker(url):
                        result["errors"].append(
                            {
                                "url": url,
                                "location": f"URL in Abstract (locale: {lang_key})"
                            }
                        )
                    else:
                        new_valid_url.append(url)
                        valid_url.append(url)

    except KeyError as e:
        missing_key = str(e)
        result["errors"].append(
            {
                "error": f"Missing key: {missing_key}",
                "location": "Metadata index structure"
            }
        )
        logger.error(f"UUID {index['_source']['uuid']}: Missing key {missing_key}")

    except Exception as e:
        result["errors"].append(
            {
                "error": str(e),
                "location": "Unexpected error during metadata processing"
            }
        )
        logger.error(f"Unexpected error for UUID {index['_source']['uuid']}: {e}")

    return result, new_valid_url


def get_message(report: list, receiver: str, user_name: str) -> object:
    """Creates an email message object"""

    message = MIMEMultipart("alternative")
    message["Subject"] = config.MAIL_SUBJECT
    message["From"] = config.MAIL_SENDER
    message["To"] = receiver
    message["X-Priority"] = "1"  # 1 (High), 3 (normal), 5 (Low)

    body_text = config.MAIL_BODY_START_TEXT.replace("{{name}}", user_name)
    body_html = config.MAIL_BODY_START_HTML.replace("{{name}}", user_name)

    for metadata in [i for i in report if len(i["errors"]) > 0]:
        body_text += f"Dataset: {config.URL_METADATA}{metadata['uuid']}\n\n"
        body_html += f"Dataset: <a href='{config.URL_METADATA}{metadata['uuid']}'>{metadata['title']}</a><br><br>"

        for error in metadata["errors"]:
            body_text += f"Invalid URL: {error['url']}\nLocation: {error['location']}\n\n"
            body_html += f"Invalid URL: <a href='{error['url']}'>{error['url']}</a><br>Location: {error['location']}<br><br>"

        body_text += "-----\n\n"
        body_html += "-----<br><br>"

    body_html += "</p></body></html>"

    message.attach(MIMEText(body_text, "plain"))
    message.attach(MIMEText(body_html, "html"))

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
