import os
import json
import logging
import hashlib
from datetime import datetime
from sftp_handler import SFTPHandler
import config

logger = logging.getLogger(__name__)

class MetadataSync:
    def __init__(self, geocat_client, sftp_handler):
        self.geocat_client = geocat_client
        self.sftp = sftp_handler
        self.cantons_config = self.load_cantons_config()
        self.local_cache_dir = "./metadata_cache"
        self.metadata_checksums = {}
        
        # Create cache directory
        os.makedirs(self.local_cache_dir, exist_ok=True)
    
    def load_cantons_config(self):
        """Load cantons configuration from JSON"""
        config_path = "./providers/organisations_smtp.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Loaded configuration for {len(data['cantons'])} cantons")
                return data['cantons']
        except Exception as e:
            logger.error(f"Error loading cantons config: {e}")
            return []
    
    def get_file_checksum(self, file_path):
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating checksum for {file_path}: {e}")
            return None
    
    def download_metadata_from_sftp(self, canton):
        """
        Download metadata files from SFTP for a specific canton
        Uses SFTP listdir (like SITG approach) - no SSH commands
        """
        logger.info(f"Downloading metadata for {canton['group_name']} from {canton['sftp_path']}")
        
        local_canton_dir = os.path.join(self.local_cache_dir, canton['slug'])
        os.makedirs(local_canton_dir, exist_ok=True)
        
        try:
            # 1. Lister les fichiers via SFTP (comme pour SITG)
            try:
                files = self.sftp.list_directory(canton['sftp_path'])
            except Exception as e:
                logger.error(f"Cannot access directory {canton['sftp_path']}: {e}")
                return []
            
            if not files:
                logger.warning(f"No files found in {canton['sftp_path']}")
                return []
            
            # 2. Filtrer par type de fichier
            if canton['file_type'] == 'xml':
                metadata_files = [f for f in files if f.lower().endswith('.xml')]
            elif canton['file_type'] == 'mef':
                metadata_files = [f for f in files if f.lower().endswith('.zip')]
            else:
                metadata_files = files
            
            logger.info(f"Found {len(metadata_files)} {canton['file_type'].upper()} files")
            
            if not metadata_files:
                logger.warning(f"No {canton['file_type']} files found in {canton['sftp_path']}")
                return []
            
            # 3. Télécharger chaque fichier localement (exactement comme SITG)
            downloaded_files = []
            for idx, filename in enumerate(metadata_files, 1):
                remote_path = f"{canton['sftp_path']}/{filename}"
                local_path = os.path.join(local_canton_dir, filename)
                
                try:
                    logger.info(f"[{idx}/{len(metadata_files)}] Downloading {filename}...")
                    self.sftp.download_file(remote_path, local_path)
                    downloaded_files.append(local_path)
                except Exception as e:
                    logger.error(f"Error downloading {filename}: {e}")
            
            logger.info(f"Successfully downloaded {len(downloaded_files)}/{len(metadata_files)} files for {canton['group_name']}")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error downloading metadata for {canton['group_name']}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def export_metadata_from_geocat(self, group_id, canton):
        """
        Export metadata from GeoNetwork for a specific group and save to SFTP
        
        Args:
            group_id: GeoNetwork group ID
            canton: Canton configuration dict
        """
        logger.info(f"Exporting metadata from GeoNetwork for group {group_id}")
        
        try:
            # Search for all metadata belonging to this group
            search_params = {
                '_owner': group_id,
                'fast': 'index',
                'from': 1,
                'to': 1000  # Adjust based on expected number of records
            }
            
            response = self.geocat_client.session.get(
                f"{self.geocat_client.env}/geonetwork/srv/api/search/records/_search",
                params=search_params,
                headers={"accept": "application/json"}
            )
            response.raise_for_status()
            search_results = response.json()
            
            metadata_list = search_results.get("metadata", [])
            logger.info(f"Found {len(metadata_list)} metadata records for {canton['group_name']}")
            
            if not metadata_list:
                logger.warning(f"No metadata found for group {group_id}")
                return []
            
            # Export each metadata as XML
            local_canton_dir = os.path.join(self.local_cache_dir, f"{canton['slug']}_export")
            os.makedirs(local_canton_dir, exist_ok=True)
            
            exported_files = []
            for md in metadata_list:
                uuid = md.get("uuid")
                if not uuid:
                    continue
                
                try:
                    # Export metadata as XML
                    export_response = self.geocat_client.session.get(
                        f"{self.geocat_client.env}/geonetwork/srv/api/records/{uuid}/formatters/xml",
                        headers={"accept": "application/xml"}
                    )
                    export_response.raise_for_status()
                    
                    # Save to local file
                    local_file = os.path.join(local_canton_dir, f"{uuid}.xml")
                    with open(local_file, 'wb') as f:
                        f.write(export_response.content)
                    
                    exported_files.append(local_file)
                    logger.info(f"Exported metadata {uuid}")
                    
                except Exception as e:
                    logger.error(f"Error exporting metadata {uuid}: {e}")
            
            logger.info(f"Exported {len(exported_files)} metadata files for {canton['group_name']}")
            return exported_files
            
        except Exception as e:
            logger.error(f"Error exporting metadata from GeoNetwork: {e}")
            return []
    
    def upload_metadata_to_geocat(self, file_paths, canton, group_id):
        """
        Upload metadata files to GeoNetwork
        
        Args:
            file_paths: List of local file paths to upload
            canton: Canton configuration dict
            group_id: GeoNetwork group ID
        """
        logger.info(f"Uploading {len(file_paths)} files to GeoNetwork for {canton['group_name']}")
        
        xsrf_token = self.geocat_client.session.cookies.get("XSRF-TOKEN")
        self.geocat_client.session.headers.update({
            "X-XSRF-TOKEN": xsrf_token,
            "accept": "application/json"
        })
        
        success_count = 0
        error_count = 0
        
        for file_path in file_paths:
            filename = os.path.basename(file_path)
            logger.info(f"Uploading: {filename}")
            
            try:
                with open(file_path, 'rb') as f:
                    # Determine file type
                    is_mef = file_path.lower().endswith('.zip')
                    content_type = 'application/zip' if is_mef else 'text/xml'
                    
                    params = {
                        'metadataType': 'METADATA',
                        'uuidProcessing': 'OVERWRITE',
                        'transformWith': 'schema:iso19115-3.2018.che:convert/fromISO19139.che',
                        'group': group_id,
                        'rejectIfInvalid': 'false',
                        'publishToAll': 'false',
                        'changeDate': 'false'
                    }
                    
                    response = self.geocat_client.session.post(
                        f"{self.geocat_client.env}/geonetwork/srv/api/records",
                        files={'file': (filename, f, content_type)},
                        params=params
                    )
                    
                    response.raise_for_status()
                    upload_response = response.json()
                    
                    # Check for errors
                    errors = upload_response.get("errors", [])
                    if errors:
                        logger.error(f"❌ Upload failed for {filename}")
                        for err in errors[:3]:
                            logger.error(f"   Error: {err.get('message', 'Unknown error')[:200]}")
                        error_count += 1
                    else:
                        num_processed = upload_response.get("numberOfRecordsProcessed", 0)
                        logger.info(f"✅ Successfully uploaded {filename} ({num_processed} record(s) processed)")
                        success_count += 1
                        
                        # Store checksum
                        checksum = self.get_file_checksum(file_path)
                        if checksum:
                            self.metadata_checksums[filename] = checksum
                
            except Exception as e:
                logger.error(f"❌ Error uploading {filename}: {e}")
                error_count += 1
        
        logger.info(f"\nUpload summary for {canton['group_name']}: {success_count} success, {error_count} errors")
        return success_count, error_count
    
    def sync_canton_metadata(self, canton, group_id):
        """
        Synchronize metadata for a specific canton (SFTP → Local → GeoNetwork)
        
        Args:
            canton: Canton configuration dict
            group_id: GeoNetwork group ID for this canton
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Syncing metadata for: {canton['group_name']}")
        logger.info(f"{'='*60}")
        
        # Step 1: Download files from SFTP to local cache
        downloaded_files = self.download_metadata_from_sftp(canton)
        
        if not downloaded_files:
            logger.warning(f"No files downloaded for {canton['group_name']}")
            return
        
        # Step 2: Upload local files to GeoNetwork
        success, errors = self.upload_metadata_to_geocat(downloaded_files, canton, group_id)
        
        logger.info(f"Sync completed for {canton['group_name']}: {success} uploaded, {errors} errors\n")
    
    def sync_all_cantons(self, group_mapping):
        """
        Sync metadata for all configured cantons
        
        Args:
            group_mapping: Dict mapping canton slug to GeoNetwork group ID
        """
        logger.info("\n" + "="*60)
        logger.info("STARTING METADATA SYNCHRONIZATION FOR ALL CANTONS")
        logger.info("="*60 + "\n")
        
        for canton in self.cantons_config:
            group_id = group_mapping.get(canton['slug'])
            
            if not group_id:
                logger.warning(f"No group ID found for {canton['slug']}, skipping")
                continue
            
            try:
                self.sync_canton_metadata(canton, group_id)
            except Exception as e:
                logger.error(f"Error syncing {canton['group_name']}: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("METADATA SYNCHRONIZATION COMPLETED")
        logger.info("="*60)