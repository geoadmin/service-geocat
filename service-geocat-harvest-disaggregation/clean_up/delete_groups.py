import logging
import os
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

def delete_all_groups(geocat, exclude_ids=None):
    """Delete all groups from GeoNetwork"""
    logger = logging.getLogger(__name__)
    exclude_ids = exclude_ids or []
    
    try:
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/groups",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        groups = response.json()
        
        logger.info(f"Found {len(groups)} groups in GeoNetwork")
        
        deleted_count = 0
        skipped_count = 0
        
        for group in groups:
            group_id = group.get("id")
            group_name = group.get("name")
            
            if group_id in exclude_ids:
                logger.info(f"Skipping protected group: '{group_name}' (ID: {group_id})")
                skipped_count += 1
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/api/groups/{group_id}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 204:
                    logger.info(f"✓ Deleted group: '{group_name}' (ID: {group_id})")
                    deleted_count += 1
                else:
                    logger.error(f"✗ Failed to delete group '{group_name}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting group '{group_name}': {e}")
        
        logger.info(f"\nDeletion complete: {deleted_count} deleted, {skipped_count} skipped")
        
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")


def delete_groups_by_pattern(geocat, pattern, exclude_ids=None):
    """Delete groups matching a specific pattern"""
    logger = logging.getLogger(__name__)
    exclude_ids = exclude_ids or []
    
    try:
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/groups",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        groups = response.json()
        
        logger.info(f"Found {len(groups)} groups. Filtering by pattern: '{pattern}'")
        
        deleted_count = 0
        skipped_count = 0
        
        for group in groups:
            group_id = group.get("id")
            group_name = group.get("name", "")
            
            if pattern.lower() not in group_name.lower():
                continue
            
            if group_id in exclude_ids:
                logger.info(f"Skipping protected group: '{group_name}' (ID: {group_id})")
                skipped_count += 1
                continue
            
            try:
                delete_response = geocat.session.delete(
                    f"{geocat.env}/geonetwork/srv/api/groups/{group_id}",
                    headers={"accept": "application/json"}
                )
                
                if delete_response.status_code == 204:
                    logger.info(f"✓ Deleted group: '{group_name}' (ID: {group_id})")
                    deleted_count += 1
                else:
                    logger.error(f"✗ Failed to delete group '{group_name}': {delete_response.status_code}")
                    
            except Exception as e:
                logger.error(f"✗ Error deleting group '{group_name}': {e}")
        
        logger.info(f"\nDeletion complete: {deleted_count} deleted, {skipped_count} skipped")
        
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")


def delete_provider_groups(geocat, source_type, exclude_ids=None):
    """
    Delete all groups from a specific source (viageo or sitg)
    
    Args:
        geocat: GeoPyCat client instance
        source_type: "viageo" or "sitg"
        exclude_ids: List of group IDs to exclude
    """
    logger = logging.getLogger(__name__)
    exclude_ids = exclude_ids or []
    
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
        
        # Get unique group slugs from providers
        group_slugs = set()
        for provider_uuid, provider in providers.items():
            if provider.get("source") == source_type:
                group_slug = provider.get("group_slug", provider.get("slug"))
                group_slugs.add(group_slug)
        
        logger.info(f"Found {len(group_slugs)} unique {source_type.upper()} groups to delete: {group_slugs}")
        
        # Fetch all groups from GeoNetwork
        response = geocat.session.get(
            f"{geocat.env}/geonetwork/srv/api/groups",
            headers={"accept": "application/json"}
        )
        response.raise_for_status()
        geocat_groups = response.json()
        
        deleted_count = 0
        skipped_count = 0
        not_found_count = 0
        
        # Delete groups that match provider slugs
        for group_slug in group_slugs:
            found = False
            
            for group in geocat_groups:
                group_id = group.get("id")
                group_name = group.get("name")
                
                if group_name == group_slug:
                    found = True
                    
                    if group_id in exclude_ids:
                        logger.info(f"Skipping protected group: '{group_name}' (ID: {group_id})")
                        skipped_count += 1
                        continue
                    
                    try:
                        delete_response = geocat.session.delete(
                            f"{geocat.env}/geonetwork/srv/api/groups/{group_id}",
                            headers={"accept": "application/json"}
                        )
                        
                        if delete_response.status_code == 204:
                            logger.info(f"✓ Deleted {source_type.upper()} group: '{group_name}' (ID: {group_id})")
                            deleted_count += 1
                        else:
                            logger.error(f"✗ Failed to delete group '{group_name}': {delete_response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"✗ Error deleting group '{group_name}': {e}")
                    
                    break
            
            if not found:
                logger.warning(f"Group '{group_slug}' not found in GeoNetwork")
                not_found_count += 1
        
        logger.info(f"\n{source_type.upper()} deletion complete: {deleted_count} deleted, {skipped_count} skipped, {not_found_count} not found")
        
    except Exception as e:
        logger.error(f"Error deleting {source_type} groups: {e}")


def main():
    load_dotenv()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    geocat = geopycat.geocat(env=config.GEOCAT_ENV)
    
    # System groups to protect
    PROTECTED_GROUP_IDS = [
        -1,  # Internet (all)
        0,   # Intranet (all)
        1,   # All
        2,   # Sample group
    ]
    
    print("\n=== GeoNetwork Group Deletion Tool ===\n")
    print("Choose an option:")
    print("1. Delete ALL groups (except protected)")
    print("2. Delete groups by pattern (e.g., 'canton', 'geneve')")
    print("3. Delete ALL Viageo groups")
    print("4. Delete ALL SITG groups")
    print("5. Cancel")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        confirm = input("\n⚠️  WARNING: This will delete ALL groups! Type 'DELETE ALL' to confirm: ")
        if confirm == "DELETE ALL":
            logger.info("Deleting all groups...")
            delete_all_groups(geocat, exclude_ids=PROTECTED_GROUP_IDS)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "2":
        pattern = input("\nEnter pattern to match (e.g., 'canton', 'geneve', 'departement'): ").strip()
        confirm = input(f"\n⚠️  This will delete all groups matching '{pattern}'. Type 'CONFIRM' to proceed: ")
        if confirm == "CONFIRM":
            logger.info(f"Deleting groups matching pattern '{pattern}'...")
            delete_groups_by_pattern(geocat, pattern, exclude_ids=PROTECTED_GROUP_IDS)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "3":
        confirm = input("\n⚠️  This will delete ALL Viageo groups. Type 'DELETE VIAGEO' to confirm: ")
        if confirm == "DELETE VIAGEO":
            logger.info("Deleting all Viageo groups...")
            delete_provider_groups(geocat, "viageo", exclude_ids=PROTECTED_GROUP_IDS)
        else:
            logger.info("Deletion cancelled.")
    
    elif choice == "4":
        confirm = input("\n⚠️  This will delete ALL SITG groups. Type 'DELETE SITG' to confirm: ")
        if confirm == "DELETE SITG":
            logger.info("Deleting all SITG groups...")
            delete_provider_groups(geocat, "sitg", exclude_ids=PROTECTED_GROUP_IDS)
        else:
            logger.info("Deletion cancelled.")
    
    else:
        logger.info("Operation cancelled.")


if __name__ == "__main__":
    main()