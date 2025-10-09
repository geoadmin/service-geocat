import os
import requests
import json
import logging
import datetime

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def upload_md(
    GEOCAT_USERNAME,
    GEOCAT_PASSWORD,
    PATH_TO_MD_FILES,
    API_URL,
    PARAMETER_UUID_PROCESSING,
    PARAMETER_GROUP,
    PARAMETER_VALIDATION,
    PARAMETER_PUBLICATION,
    # UPDATE_DATE_STAMP,
    PROXY_HTTP,
    PROXY_HTTPS
):
    session = requests.Session()
    session.auth = (GEOCAT_USERNAME, GEOCAT_PASSWORD)

    # Use proxies passed as parameters or default to empty strings
    http_proxy = PROXY_HTTP or ""
    https_proxy = PROXY_HTTPS or ""
    if http_proxy or https_proxy:
        session.proxies.update({
            "http": http_proxy,
            "https": https_proxy
        })
        logging.info(f"Using proxies: {session.proxies}")

    try:
        response = session.get(f"{API_URL}/me", headers={"accept": "application/json"})
        response.raise_for_status()
        xsrf_token = response.cookies.get("XSRF-TOKEN")
        session.headers.update({
            "X-XSRF-TOKEN": xsrf_token,
            "accept": "application/json"
        })
        logging.info("Authenticated successfully.")
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        if response is not None:
            logging.error(f"Response content: {response.content}")
        return

    xml_files = [
        os.path.join(PATH_TO_MD_FILES, f)
        for f in os.listdir(PATH_TO_MD_FILES)
        if f.lower().endswith('.xml')
    ]

    if not xml_files:
        logging.warning("No XML files found in the directory.")
        return

    for xml_file in xml_files:
        logging.info(f"Uploading XML: {xml_file}")
        try:
            with open(xml_file, 'rb') as f:
                response = session.post(
                    f"{API_URL}/records",
                    files={'file': (xml_file, f, 'text/xml')},
                    params={
                        'metadataType': 'METADATA',
                        'uuidProcessing': PARAMETER_UUID_PROCESSING,
                        'group': PARAMETER_GROUP,
                        'rejectIfInvalid': PARAMETER_VALIDATION,
                        'publishToAll': PARAMETER_PUBLICATION,
                        # 'changeDate': 'now',
                    }
                )
                response.raise_for_status()
                upload_response = response.json()
                logging.info(f"Upload response: {json.dumps(upload_response, indent=2)}")

                # --- NOT USED ANYMORE ---
                # if UPDATE_DATE_STAMP:
                #     metadata_infos = upload_response.get('metadataInfos', {})
                #     if not metadata_infos:
                #         logging.warning("No metadataInfos in upload response, skipping date update")
                #         continue
                    
                #     first_group = next(iter(metadata_infos.values()), None)
                #     if not first_group or not first_group[0]:
                #         logging.warning("No metadata group found, skipping date update")
                #         continue
                    
                #     uuid = first_group[0].get('uuid')
                #     if not uuid:
                #         logging.warning("No UUID found in metadata group, skipping date update")
                #         continue
                    
                #     now_iso = datetime.datetime.now().isoformat(timespec='seconds')

                #     update_url = f"{API_URL}/records/batchediting"
                #     params = {
                #         "uuids": uuid,
                #         "updateDateStamp": "true"
                #     }
                #     payload = [
                #         {
                #         "xpath": ".//gmd:identificationInfo//gmd:citation//gmd:date/*[gmd:dateType/*/@codeListValue='revision']/gmd:date/gco:DateTime",
                #         "value": now_iso,
                #         "condition": ""
                #         }
                #     ]
                    
                #     response = session.put(
                #         update_url,
                #         params=params,
                #         json=payload
                #     )
                #     response.raise_for_status()
                #     logging.info(f"Successfully updated dateStamp for UUID {uuid} with value {now_iso}")
                # else:
                #     logging.info("UPDATE_DATE_STAMP is False, skipping date update")
                
        except Exception as e:
            logging.error(f"Error processing {xml_file}: {e}")
            if 'response' in locals():
                logging.error(f"Response content: {response.content}")

    mef_files = [
        os.path.join(PATH_TO_MD_FILES, f)
        for f in os.listdir(PATH_TO_MD_FILES)
        if f.lower().endswith('.zip')
    ]

    for mef_file in mef_files:
        logging.info(f"Uploading MEF: {mef_file}")
        try:
            with open(mef_file, 'rb') as f:
                response = session.post(
                    f"{API_URL}/records",
                    files={'file': (os.path.basename(mef_file), f, 'application/zip')},
                    params={
                        'metadataType': 'METADATA',
                        'uuidProcessing': PARAMETER_UUID_PROCESSING,
                        'group': PARAMETER_GROUP,
                        # 'changeDate': 'now'
                    }
                )
                response.raise_for_status()
                upload_response = response.json()
                logging.info(f"MEF upload response: {json.dumps(upload_response, indent=2)}")

                mef_uuid = upload_response.get("uuid")
                if not mef_uuid:
                    logging.warning("No UUID found for MEF, skipping post-upload actions")
                    continue

                # Step 1: Check DOI URL (get real uuid)
                doi_url = f"{API_URL}/records/{mef_uuid}/doi/checkDoiUrl"
                doi_resp = session.get(doi_url)
                doi_resp.raise_for_status()
                real_uuid = doi_resp.text.strip().lstrip('/')
                logging.info(f"Real UUID for MEF {mef_file}: {real_uuid}")

                # Step 2: Validate MEF if PARAMETER_VALIDATION is True
                if PARAMETER_VALIDATION == "True":
                    validate_url = f"{API_URL}/records/validate"
                    validate_params = {'uuids': real_uuid}
                    v_resp = session.post(validate_url, params=validate_params)
                    v_resp.raise_for_status()
                    logging.info(f"Validation response for {real_uuid}: {v_resp.json()}")

                # Step 3: Publish MEF if PARAMETER_PUBLICATION is True
                if PARAMETER_PUBLICATION == "True":
                    publish_url = f"{API_URL}/records/{real_uuid}/publish"
                    p_resp = session.post(publish_url)
                    p_resp.raise_for_status()
                    logging.info(f"Publish response for {real_uuid}: {p_resp.json()}")

        except Exception as e:
            logging.error(f"Error processing MEF {mef_file}: {e}")
            if 'response' in locals():
                logging.error(f"Response content: {response.content}")