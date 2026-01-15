import logging
from dotenv import load_dotenv
import config
import geopycat

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M'
    )

def delete_all_logos(geocat, exclude_logos=None):
    """
    Delete all logos from GeoNetwork
    
    Args:
        geocat: GeoPyCat client instance
        exclude_logos: List of logo filenames to exclude from deletion
    """
    logger = logging.getLogger(__name__)
    exclude_logos = exclude_logos or []
    
    try:
        # Fetch all logos
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/logos",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        logos = response.json()
        
        logger.info(f"Found {len(logos)} logos in GeoNetwork")
        
        deleted_count = 0
        skipped_count = 0
        
        for logo_filename in logos:
            if not isinstance(logo_filename, str):
                logger.warning(f"Unexpected logo format: {logo_filename}")
                continue
            
            if logo_filename in exclude_logos:
                logger.info(f"Skipping protected logo: '{logo_filename}'")
                skipped_count += 1
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/api/logos/{logo_filename}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 204:
                    logger.info(f"✓ Deleted logo: '{logo_filename}'")
                    deleted_count += 1
                elif delete_response.status_code == 404:
                    logger.warning(f"⚠ Logo not found: '{logo_filename}'")
                else:
                    logger.error(f"✗ Failed to delete logo '{logo_filename}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting logo '{logo_filename}': {e}")
        
        logger.info(f"\nDeletion complete: {deleted_count} deleted, {skipped_count} skipped")
        
    except Exception as e:
        logger.error(f"Error fetching logos: {e}")


def delete_logos_by_pattern(geocat, pattern, exclude_logos=None):
    """
    Delete logos matching a specific pattern
    
    Args:
        geocat: GeoPyCat client instance
        pattern: String pattern to match in logo filenames
        exclude_logos: List of logo filenames to exclude
    """
    logger = logging.getLogger(__name__)
    exclude_logos = exclude_logos or []
    
    try:
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/logos",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        logos = response.json()
        
        logger.info(f"Found {len(logos)} logos. Filtering by pattern: '{pattern}'")
        
        deleted_count = 0
        skipped_count = 0
        
        for logo_filename in logos:
            if not isinstance(logo_filename, str):
                continue
            
            if pattern.lower() not in logo_filename.lower():
                continue
            
            if logo_filename in exclude_logos:
                logger.info(f"Skipping protected logo: '{logo_filename}'")
                skipped_count += 1
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/api/logos/{logo_filename}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 204:
                    logger.info(f"✓ Deleted logo: '{logo_filename}'")
                    deleted_count += 1
                else:
                    logger.error(f"✗ Failed to delete logo '{logo_filename}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting logo '{logo_filename}': {e}")
        
        logger.info(f"\nDeletion complete: {deleted_count} deleted, {skipped_count} skipped")
        
    except Exception as e:
        logger.error(f"Error fetching logos: {e}")


def delete_logos_by_source(geocat, source_type, exclude_logos=None):
    """
    Delete logos from a specific source folder (Viageo or SITG)
    
    Args:
        geocat: GeoPyCat client instance
        source_type: "viageo" or "sitg"
        exclude_logos: List of logo filenames to exclude
    """
    logger = logging.getLogger(__name__)
    exclude_logos = exclude_logos or []
    
    try:
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/logos",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        logos = response.json()
        
        # Determine the prefix based on source
        if source_type == "viageo":
            prefix = "viageo/"
        elif source_type == "sitg":
            prefix = "SITG/"
        else:
            logger.error(f"Unknown source type: {source_type}")
            return
        
        logger.info(f"Found {len(logos)} logos. Filtering by source: '{source_type.upper()}'")
        
        deleted_count = 0
        skipped_count = 0
        
        for logo_filename in logos:
            if not isinstance(logo_filename, str):
                continue
            
            # Check if logo belongs to the source folder
            if not logo_filename.startswith(prefix):
                continue
            
            if logo_filename in exclude_logos:
                logger.info(f"Skipping protected logo: '{logo_filename}'")
                skipped_count += 1
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/api/logos/{logo_filename}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 204:
                    logger.info(f"✓ Deleted {source_type.upper()} logo: '{logo_filename}'")
                    deleted_count += 1
                else:
                    logger.error(f"✗ Failed to delete logo '{logo_filename}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting logo '{logo_filename}': {e}")
        
        logger.info(f"\n{source_type.upper()} logo deletion complete: {deleted_count} deleted, {skipped_count} skipped")
        
    except Exception as e:
        logger.error(f"Error deleting {source_type} logos: {e}")


def main():
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    geocat = geopycat.geocat(env=config.GEOCAT_ENV)
    
    # Protected logos (system defaults)
    PROTECTED_LOGOS = [
        "default_logo.png",
        "geocat_logo.png",
    ]
    
    print("\n=== GeoNetwork Logo Deletion Tool ===\n")
    print("Choose an option:")
    print("1. Delete ALL logos (except protected)")
    print("2. Delete logos by pattern (e.g., 'canton', 'png')")
    print("3. Delete ALL Viageo logos")
    print("4. Delete ALL SITG logos")
    print("5. Cancel")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        confirm = input("\n⚠️  WARNING: This will delete ALL logos! Type 'DELETE ALL LOGOS' to confirm: ")
        if confirm == "DELETE ALL LOGOS":
            logger.info("Deleting all logos...")
            delete_all_logos(geocat, exclude_logos=PROTECTED_LOGOS)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "2":
        pattern = input("\nEnter pattern to match (e.g., 'canton', 'geneve', '.png'): ").strip()
        confirm = input(f"\n⚠️  This will delete all logos matching '{pattern}'. Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            logger.info(f"Deleting logos matching pattern '{pattern}'...")
            delete_logos_by_pattern(geocat, pattern, exclude_logos=PROTECTED_LOGOS)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "3":
        confirm = input("\n⚠️  This will delete ALL Viageo logos. Type 'DELETE VIAGEO LOGOS' to confirm: ")
        if confirm == "DELETE VIAGEO LOGOS":
            logger.info("Deleting all Viageo logos...")
            delete_logos_by_source(geocat, "viageo", exclude_logos=PROTECTED_LOGOS)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "4":
        confirm = input("\n⚠️  This will delete ALL SITG logos. Type 'DELETE SITG LOGOS' to confirm: ")
        if confirm == "DELETE SITG LOGOS":
            logger.info("Deleting all SITG logos...")
            delete_logos_by_source(geocat, "sitg", exclude_logos=PROTECTED_LOGOS)
        else:
            logger.info("Deletion cancelled.")
    
    else:
        logger.info("Operation cancelled.")


if __name__ == "__main__":
    main()