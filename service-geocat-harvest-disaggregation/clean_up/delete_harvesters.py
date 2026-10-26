import logging
from dotenv import load_dotenv
import config
import geopycat
from providers import ProviderManager

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M'
    )

def delete_all_harvesters(geocat):
    """Delete all harvesters from GeoNetwork"""
    logger = logging.getLogger(__name__)
    
    try:
        # Fetch all harvesters
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/eng/admin.harvester.list?_content_type=json",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        harvesters = response.json()
        
        logger.info(f"Found {len(harvesters)} harvesters in GeoNetwork")
        
        deleted_count = 0
        
        for harvester in harvesters:
            if not isinstance(harvester, dict):
                continue
            
            harvester_id = harvester.get("@id")
            harvester_name = harvester.get("site", {}).get("name", "Unknown")
            
            if not harvester_id:
                logger.warning(f"Harvester '{harvester_name}' has no ID, skipping")
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/eng/admin.harvester.remove?_content_type=json&id={harvester_id}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 200:
                    logger.info(f"✓ Deleted harvester: '{harvester_name}' (ID: {harvester_id})")
                    deleted_count += 1
                else:
                    logger.error(f"✗ Failed to delete harvester '{harvester_name}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting harvester '{harvester_name}': {e}")
        
        logger.info(f"\nDeletion complete: {deleted_count} harvesters deleted")
        
    except Exception as e:
        logger.error(f"Error fetching harvesters: {e}")


def delete_harvesters_by_pattern(geocat, pattern):
    """Delete harvesters matching a specific pattern"""
    logger = logging.getLogger(__name__)
    
    try:
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/eng/admin.harvester.list?_content_type=json",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        harvesters = response.json()
        
        logger.info(f"Found {len(harvesters)} harvesters. Filtering by pattern: '{pattern}'")
        
        deleted_count = 0
        skipped_count = 0
        
        for harvester in harvesters:
            if not isinstance(harvester, dict):
                continue
            
            harvester_id = harvester.get("@id")
            harvester_name = harvester.get("site", {}).get("name", "")
            
            if pattern.lower() not in harvester_name.lower():
                continue
            
            if not harvester_id:
                logger.warning(f"Harvester '{harvester_name}' has no ID, skipping")
                skipped_count += 1
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/eng/admin.harvester.remove?_content_type=json&id={harvester_id}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 200:
                    logger.info(f"✓ Deleted harvester: '{harvester_name}' (ID: {harvester_id})")
                    deleted_count += 1
                else:
                    logger.error(f"✗ Failed to delete harvester '{harvester_name}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting harvester '{harvester_name}': {e}")
        
        logger.info(f"\nDeletion complete: {deleted_count} deleted, {skipped_count} skipped")
        
    except Exception as e:
        logger.error(f"Error fetching harvesters: {e}")


def delete_provider_harvesters(geocat, source_type):
    """
    Delete all harvesters from a specific source (viageo or sitg)
    
    Args:
        geocat: GeoPyCat client instance
        source_type: "viageo" or "sitg"
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Load providers
        provider_manager = ProviderManager()
        
        if source_type == "viageo":
            logger.info("Loading Viageo providers...")
            provider_manager.load_viageo_providers(geocat)
        elif source_type == "sitg":
            logger.info("Loading SITG providers...")
            provider_manager.load_sitg_providers()
        else:
            logger.error(f"Unknown source type: {source_type}")
            return
        
        providers = provider_manager.get_all_providers()
        
        # Get all provider slugs (these are harvester names)
        provider_slugs = set()
        for provider_uuid, provider in providers.items():
            if provider.get("source") == source_type:
                provider_slugs.add(provider.get("slug"))
        
        logger.info(f"Found {len(provider_slugs)} {source_type.upper()} providers: {sorted(provider_slugs)}")
        
        # Fetch all harvesters
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/eng/admin.harvester.list?_content_type=json",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        harvesters = response.json()
        
        logger.info(f"Found {len(harvesters)} harvesters in GeoNetwork")
        
        deleted_count = 0
        not_found_count = 0
        
        # Delete harvesters matching provider slugs
        for provider_slug in provider_slugs:
            found = False
            
            for harvester in harvesters:
                if not isinstance(harvester, dict):
                    continue
                
                harvester_id = harvester.get("@id")
                harvester_name = harvester.get("site", {}).get("name", "")
                
                if harvester_name == provider_slug:
                    found = True
                    
                    if not harvester_id:
                        logger.warning(f"Harvester '{harvester_name}' has no ID, skipping")
                        continue
                    
                    try:
                        delete_response = geocat.session.delete(
                            f"{geocat.env}/geonetwork/srv/eng/admin.harvester.remove?_content_type=json&id={harvester_id}",
                            headers={"accept": "application/json"}
                        )
                        
                        if delete_response.status_code == 200:
                            logger.info(f"✓ Deleted {source_type.upper()} harvester: '{harvester_name}' (ID: {harvester_id})")
                            deleted_count += 1
                        else:
                            logger.error(f"✗ Failed to delete harvester '{harvester_name}': {delete_response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"✗ Error deleting harvester '{harvester_name}': {e}")
                    
                    break
            
            if not found:
                logger.debug(f"Harvester '{provider_slug}' not found in GeoNetwork")
                not_found_count += 1
        
        logger.info(f"\n{source_type.upper()} deletion complete: {deleted_count} deleted, {not_found_count} not found")
        
    except Exception as e:
        logger.error(f"Error deleting {source_type} harvesters: {e}")


def main():
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    geocat = geopycat.geocat(env=config.GEOCAT_ENV)
    
    print("\n=== GeoNetwork Harvester Deletion Tool ===\n")
    print("Choose an option:")
    print("1. Delete ALL harvesters")
    print("2. Delete harvesters by pattern (e.g., 'canton', 'departement')")
    print("3. Delete ALL Viageo harvesters")
    print("4. Delete ALL SITG harvesters")
    print("5. Cancel")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        confirm = input("\n⚠️  WARNING: This will delete ALL harvesters! Type 'DELETE ALL HARVESTERS' to confirm: ")
        if confirm == "DELETE ALL HARVESTERS":
            logger.info("Deleting all harvesters...")
            delete_all_harvesters(geocat)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "2":
        pattern = input("\nEnter pattern to match (e.g., 'canton', 'geneve', 'departement'): ").strip()
        confirm = input(f"\n⚠️  This will delete all harvesters matching '{pattern}'. Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            logger.info(f"Deleting harvesters matching pattern '{pattern}'...")
            delete_harvesters_by_pattern(geocat, pattern)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "3":
        confirm = input("\n⚠️  This will delete ALL Viageo harvesters. Type 'DELETE VIAGEO' to confirm: ")
        if confirm == "DELETE VIAGEO":
            logger.info("Deleting all Viageo harvesters...")
            delete_provider_harvesters(geocat, "viageo")
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "4":
        confirm = input("\n⚠️  This will delete ALL SITG harvesters. Type 'DELETE SITG' to confirm: ")
        if confirm == "DELETE SITG":
            logger.info("Deleting all SITG harvesters...")
            delete_provider_harvesters(geocat, "sitg")
        else:
            logger.info("Deletion cancelled.")
    
    else:
        logger.info("Operation cancelled.")


if __name__ == "__main__":
    main()