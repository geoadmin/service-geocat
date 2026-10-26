import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import config
import geopycat
from sftp_handler import SFTPHandler
from metadata_sync import MetadataSync

def setup_logging():
    """Setup logging configuration"""
    logs_dir = config.LOGS_DIR
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    logfile = f"metadata_sync_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
    log_file_path = os.path.join(logs_dir, logfile)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def fetch_geocat_groups(geocat):
    """Fetch all groups from GeoNetwork and build mapping by name"""
    logger = logging.getLogger(__name__)
    try:
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/groups",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        groups = response.json()
        
        # Build mapping: group name -> group ID
        group_mapping = {}
        
        for group in groups:
            group_id = group.get("id")
            group_name = group.get("name")
            
            if group_name and group_id:
                group_mapping[group_name] = group_id
        
        logger.info(f"Retrieved {len(groups)} groups from GeoNetwork")
        logger.debug(f"Group mapping: {len(group_mapping)} entries")
        
        return group_mapping
        
    except Exception as e:
        logger.error(f"Error fetching GeoNetwork groups: {e}")
        return {}

def build_canton_group_mapping(cantons_config, group_mapping):
    """
    Build mapping from canton slug to GeoNetwork group ID
    Uses the exact group_name from JSON to match GeoNetwork groups
    """
    logger = logging.getLogger(__name__)
    canton_to_group_id = {}
    
    for canton in cantons_config:
        slug = canton['slug']
        group_name = canton['group_name']
        
        # Find group by exact name
        group_id = group_mapping.get(group_name)
        
        if group_id:
            canton_to_group_id[slug] = group_id
            logger.debug(f"Matched '{slug}' using group name '{group_name}' -> group ID {group_id}")
        else:
            logger.warning(f"No group found with name '{group_name}' for canton '{slug}'")
    
    return canton_to_group_id

def main():
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info("CANTON METADATA SYNCHRONIZATION - STANDALONE")
    logger.info("="*80)
    
    # Initialize GeoNetwork connection
    logger.info(f"Connecting to GeoNetwork environment: {config.GEOCAT_ENV}")
    geocat = geopycat.geocat(env=config.GEOCAT_ENV)
    
    # Fetch existing groups from GeoNetwork
    logger.info("Fetching groups from GeoNetwork...")
    group_mapping = fetch_geocat_groups(geocat)
    
    if not group_mapping:
        logger.error("No groups found in GeoNetwork.")
        return
    
    # Create SFTP connection
    logger.info(f"Connecting to SFTP server: {config.SFTP_HOST}")
    sftp = SFTPHandler(
        host=config.SFTP_HOST,
        username=config.SFTP_USERNAME,
        private_key_path=config.SFTP_PRIVATE_KEY_PATH
    )
    sftp.connect()
    
    # Create metadata sync instance
    logger.info("Initializing metadata synchronization...")
    metadata_sync = MetadataSync(geocat, sftp)
    
    # Build canton -> group ID mapping
    logger.info("Building canton to group mapping...")
    canton_group_mapping = build_canton_group_mapping(
        metadata_sync.cantons_config, 
        group_mapping
    )
    
    # Display available cantons
    logger.info(f"\nFound {len(metadata_sync.cantons_config)} cantons configured:")
    for idx, canton in enumerate(metadata_sync.cantons_config, 1):
        group_id = canton_group_mapping.get(canton['slug'])
        status = f"✓ Group found (ID: {group_id})" if group_id else "✗ Group NOT found"
        logger.info(f"  {idx}. {canton['group_name']} ({canton['slug']}) - {status}")
    
    # Interactive menu
    print("\n" + "="*80)
    print("SYNCHRONIZATION OPTIONS")
    print("="*80)
    print("1. Sync ALL cantons")
    print("2. Sync a SPECIFIC canton")
    print("3. Test SFTP connection only (list files)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        logger.info("\nStarting synchronization for ALL cantons...")
        metadata_sync.sync_all_cantons(canton_group_mapping)
    
    elif choice == "2":
        print("\nAvailable cantons:")
        for idx, canton in enumerate(metadata_sync.cantons_config, 1):
            group_id = canton_group_mapping.get(canton['slug'])
            status = "✓" if group_id else "✗"
            print(f"  {idx}. {status} {canton['group_name']} ({canton['slug']})")
        
        try:
            canton_idx = int(input("\nEnter canton number: ").strip()) - 1
            if 0 <= canton_idx < len(metadata_sync.cantons_config):
                selected_canton = metadata_sync.cantons_config[canton_idx]
                group_id = canton_group_mapping.get(selected_canton['slug'])
                
                if not group_id:
                    logger.error(f"Group '{selected_canton['group_name']}' not found in GeoNetwork!")
                    logger.error("Please create the group first or check the name matches exactly.")
                else:
                    logger.info(f"\nSyncing {selected_canton['group_name']} (group ID: {group_id})...")
                    metadata_sync.sync_canton_metadata(selected_canton, group_id)
            else:
                logger.error("Invalid canton number")
        except ValueError:
            logger.error("Invalid input")
    
    elif choice == "3":
        print("\nTesting SFTP connection...")
        print("Available cantons:")
        for idx, canton in enumerate(metadata_sync.cantons_config, 1):
            print(f"  {idx}. {canton['group_name']} - {canton['sftp_path']}")
        
        # Add option to test root directory
        print(f"  0. Test root directory (/mnt/s3)")
        
        try:
            canton_idx = input("\nEnter canton number to test (or 0 for root): ").strip()
            
            if canton_idx == "0":
                # Test root directory
                logger.info("\nListing root directory /mnt/s3...")
                try:
                    files = sftp.list_directory("/mnt/s3")
                    logger.info(f"Found {len(files)} directories in /mnt/s3:")
                    for f in sorted(files):
                        logger.info(f"  - {f}")
                except Exception as e:
                    logger.error(f"Error listing root directory: {e}")
            else:
                canton_idx = int(canton_idx) - 1
                if 0 <= canton_idx < len(metadata_sync.cantons_config):
                    selected_canton = metadata_sync.cantons_config[canton_idx]
                    logger.info(f"\nTesting access to {selected_canton['sftp_path']}...")
                    
                    try:
                        # First check if directory exists
                        try:
                            sftp.sftp.stat(selected_canton['sftp_path'])
                            logger.info(f"✓ Directory exists: {selected_canton['sftp_path']}")
                        except FileNotFoundError:
                            logger.error(f"✗ Directory NOT found: {selected_canton['sftp_path']}")
                            
                            # Try to list parent directory
                            parent_path = os.path.dirname(selected_canton['sftp_path'])
                            logger.info(f"Trying parent directory: {parent_path}")
                            try:
                                parent_files = sftp.list_directory(parent_path)
                                logger.info(f"Found {len(parent_files)} items in parent:")
                                for f in sorted(parent_files):
                                    logger.info(f"  - {f}")
                            except Exception as e2:
                                logger.error(f"Cannot access parent either: {e2}")
                            return
                        
                        # Try to list files
                        files = sftp.list_directory(selected_canton['sftp_path'])
                        logger.info(f"Found {len(files)} files:")
                        
                        # Filter by file type
                        if selected_canton['file_type'] == 'xml':
                            filtered_files = [f for f in files if f.lower().endswith('.xml')]
                        elif selected_canton['file_type'] == 'mef':
                            filtered_files = [f for f in files if f.lower().endswith('.zip')]
                        else:
                            filtered_files = files
                        
                        logger.info(f"Files matching type '{selected_canton['file_type']}': {len(filtered_files)}")
                        for f in filtered_files[:20]:  # Show first 20
                            logger.info(f"  - {f}")
                        
                        if len(filtered_files) > 20:
                            logger.info(f"  ... and {len(filtered_files) - 20} more files")
                            
                    except Exception as e:
                        logger.error(f"Error accessing directory: {e}")
                        logger.error(f"Error type: {type(e).__name__}")
                        
                        # Suggest checking permissions
                        logger.info("\n💡 TROUBLESHOOTING:")
                        logger.info(f"  1. Verify SFTP user has read access to: {selected_canton['sftp_path']}")
                        logger.info(f"  2. Check if path is correct (case-sensitive)")
                        logger.info(f"  3. Try listing parent directory to see available subdirectories")
                else:
                    logger.error("Invalid canton number")
        except ValueError:
            logger.error("Invalid input")
    
    else:
        logger.info("Exiting...")
    
    # Cleanup
    sftp.close()
    logger.info("\n" + "="*80)
    logger.info("METADATA SYNCHRONIZATION COMPLETED")
    logger.info("="*80)

if __name__ == "__main__":
    main()