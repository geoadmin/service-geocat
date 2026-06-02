import os
import sys
import copy
from dotenv import load_dotenv
import config
import geopycat
import logging
import logging.config
from datetime import datetime

logs_dir = os.path.join(os.path.dirname(__file__), "logs")

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

logfile = f"{datetime.now().strftime('%Y%m%d%H%M%S')}.log"

log_config = geopycat.utils.get_log_config(os.path.join(logs_dir, logfile))
logging.config.dictConfig(log_config)

import link_checker

load_dotenv()

logger = logging.getLogger(__name__)

# TEST_MODE: if True, all emails are sent only to TEST_EMAIL via a local SMTP (e.g. MailHog)
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
TEST_EMAIL = os.environ.get("TEST_EMAIL", config.MAIL_SENDER)
USER_FILTER = os.environ.get("USER_FILTER", "").strip()

if TEST_MODE:
    logger.warning("Running in TEST_MODE - all emails will be sent to %s", TEST_EMAIL)
if USER_FILTER:
    logger.warning("USER_FILTER active - processing only username: %s", USER_FILTER)

geocat = geopycat.geocat(env="prod")

# Set proxies in environment variables
# os.environ["HTTP_PROXY"] = geocat.session.proxies.get["http"]
# os.environ["HTTPS_PROXY"] = geocat.session.proxies.get["https"]
http_proxy = geocat.session.proxies.get("http")
https_proxy = geocat.session.proxies.get("https")

if http_proxy:
    os.environ["HTTP_PROXY"] = http_proxy
if https_proxy:
    os.environ["HTTPS_PROXY"] = https_proxy


try:
    users = geocat.get_users(owner_only=True)
except Exception as e:
    logger.error("Cannot retrieve users information: %s", str(e))
    sys.exit()

user_count = 0

# Global cache of valid URLs across all users - avoids re-testing the same URL
valid_url = []

for user in users:

    user_count += 1

    # Skip users not matching USER_FILTER (if set)
    if USER_FILTER and user["username"] != USER_FILTER:
        continue

    logger.info("Processing User [%s/%s] ID: %s (%s %s)",
                user_count, len(users), user["id"], user["name"], 
                user["surname"])

    query = geopycat.utils.get_search_query(published_only=True,
                                            q=f"owner:{user['id']}")

    body = copy.deepcopy(config.SEARCH_API_BODY)
    body["query"] = query

    try:
        indexes = geocat.es_deep_search(body=body)
    except Exception as e:
        logger.error("User [%s/%s] ID: %s - unable to retrieve metadata index: %s",
                     user_count, len(users), user["id"], str(e))
        continue

    if len(indexes) == 0:
        logger.warning("User [%s/%s] ID: %s - no published metadata",
                       user_count, len(users), user["id"]) 
        continue

    # In TEST_MODE, send all emails only to TEST_EMAIL
    # In production, send to the metadata owner and to MAIL_SENDER
    if TEST_MODE:
        receivers = [TEST_EMAIL]
    else:
        receivers = [user["emailAddresses"][0], config.MAIL_SENDER]

    # list of tested URL that are valid
    # We do not test them again (shared across all users)

    report = []

    count = 0

    for index in indexes:

        count += 1
        logger.info("metadata processed : %s - %s%%", index["_source"]["uuid"],
                    round((count / len(indexes)) * 100, 1))

        result, new_valid_url = link_checker.check_metadata_url(index=index,
                                                     valid_url=valid_url)

        report.append(result)
        valid_url += new_valid_url

    if len([i for i in report if len(i["errors"]) > 0]) > 0:
        message = link_checker.get_message(report=report,
                                            receiver=receivers[0],
                                            user_name=user['username'])

        try:
            link_checker.send_email(receivers=receivers, message=message)

        except Exception as e:
            logger.exception(e)

        else:
            log_dest = TEST_EMAIL if TEST_MODE else user["emailAddresses"][0]
            logger.info("User [%s/%s] ID: %s (%s %s) - Mail sent to %s%s",
                        user_count, len(users), user["id"], user["name"],
                        user["surname"], log_dest,
                        " [TEST MODE]" if TEST_MODE else "")

    else:
        logger.info("User [%s/%s] ID: %s (%s %s) - has no invalid URL",
                    user_count, len(users), user["id"], user["name"],
                    user["surname"])
