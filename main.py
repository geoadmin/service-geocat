import os
import sys
import copy
from dotenv import load_dotenv
import config
import argparse
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

import utils

load_dotenv()

# HARVESTER_ONLY override order: CLI -> env var -> config
# CLI flags: --harvester-only (only harvesters), --all-partners (include local)
harvester_only_flag = config.HARVESTER_ONLY
env_val = os.environ.get("HARVESTER_ONLY")
if env_val is not None:
    if env_val.lower() in ("1", "true", "yes", "y"):
        harvester_only_flag = True
    elif env_val.lower() in ("0", "false", "no", "n"):
        harvester_only_flag = False

parser = argparse.ArgumentParser(add_help=False)
group = parser.add_mutually_exclusive_group()
group.add_argument("--harvester-only", dest="harvester_only", action="store_true", help="Target only harvesters")
group.add_argument("--all-partners", dest="harvester_only", action="store_false", help="Target all partners (local + harvested)")
parser.set_defaults(harvester_only=None)
args, _ = parser.parse_known_args()
if args.harvester_only is not None:
    harvester_only_flag = args.harvester_only

logger = logging.getLogger(__name__)

geocat = geopycat.geocat(env="prod")

# Determine whether to request only harvesters or all users
harvester_only_flag = getattr(config, "HARVESTER_ONLY", True)

try:
    try:
        users = geocat.get_users(harvester_only=harvester_only_flag)
    except Exception:
        logger.warning("Failed to retrieve users — waiting for connectivity and retrying...")
        import utils as _utils
        _utils._wait_for_connectivity()
        users = geocat.get_users(harvester_only=harvester_only_flag)
except Exception:
    logger.exception("Cannot retrieve users information")
    sys.exit(1)

user_count = 0

# If HARVESTER_ONLY is False, we target all partners and should use the
# alternate mail body texts.
all_partners = not harvester_only_flag

for user in users:

    user_count += 1

    logger.info("Processing User [%s/%s] ID: %s (%s %s)",
                user_count, len(users), user["id"], user["name"], 
                user["surname"])

    query = geopycat.utils.get_search_query(published_only=True,
                        q=f"owner:{user['id']}")

    body = copy.deepcopy(config.SEARCH_API_BODY)
    body["query"] = query

    try:
        indexes = geocat.es_deep_search(body=body)
    except:
        logger.error("User [%s/%s] ID: %s - unable to retreieve metadata index",
                user_count, len(users), user["id"])
        continue

    if len(indexes) == 0:
        logger.warning("User [%s/%s] ID: %s - no published metadata",
                user_count, len(users), user["id"]) 
        continue

    # For Production, send email to group admin and to receiver
    # receivers = [user["emailAddresses"][0], config.MAIL_SENDER]

    # For test purpose, send email only to the sender
    receivers = [config.MAIL_SENDER]

    invalid_metadata = []

    count = 0

    for index in indexes:

        count += 1

        valid = utils.check_md_validity(geocat, index["_source"]["uuid"])

        if valid is False:

            invalid_metadata.append(
                {
                    "uuid": index["_source"]["uuid"],
                    "title": index["_source"]["resourceTitleObject"]["default"]
                }
            )

            logger.info("metadata processed [%s/%s] : %s - Not Valid",
                count, len(indexes), index["_source"]["uuid"])

        elif valid is True:

            logger.info("metadata processed [%s/%s] : %s - Valid",
                count, len(indexes), index["_source"]["uuid"])

    if len(invalid_metadata) > 0:
        message = utils.get_message(invalid_metadata=invalid_metadata,
                            receiver=receivers[0],
                            user_name=user['username'],
                            all_partners=all_partners)

        host = os.environ.get("SMTP_ENDPOINT")

        try:
            utils.send_email(receivers=receivers, message=message)

        except Exception as e:
            logger.exception(e)

        else:
            logger.info("User [%s/%s] ID: %s (%s %s) - Mail sent to %s",
                        user_count, len(users), user["id"], user["name"],
                        user["surname"], user["emailAddresses"][0])

    else:
        logger.info("User [%s/%s] ID: %s (%s %s) - has no invalid metadata",
                    user_count, len(users), user["id"], user["name"],
                    user["surname"])
