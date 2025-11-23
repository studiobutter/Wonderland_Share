"""Database utility functions for cached images."""
from config.database import get_session, CachedImage
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


def get_cached_image(guid: str, server: str) -> dict | None:
    """
    Retrieve a cached image from the database.
    
    Args:
        guid: The GUID of the level
        server: The server region
        
    Returns:
        Dictionary with image_url if found, None otherwise
    """
    try:
        session = get_session()
        cached = session.query(CachedImage).filter(
            CachedImage.guid == guid,
            CachedImage.server == server
        ).first()
        
        if cached:
            return {
                'image_url': cached.image_url,
                'created_at': cached.created_at,
                'updated_at': cached.updated_at
            }
        return None
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving cached image: {e}")
        return None
    finally:
        session.close()


def save_cached_image(guid: str, server: str, image_url: str, original_url: str | None = None) -> bool:
    """
    Save a cached image to the database.
    
    Args:
        guid: The GUID of the level
        server: The server region
        image_url: The Discord CDN URL for the image
        original_url: Optional original endpoint URL
        
    Returns:
        True if successful, False otherwise
    """
    try:
        session = get_session()
        
        # Check if already exists
        existing = session.query(CachedImage).filter(
            CachedImage.guid == guid,
            CachedImage.server == server
        ).first()
        
        if existing:
            # Update existing record
            existing.image_url = image_url
            existing.original_url = original_url
            logger.info(f"Updated cached image for GUID {guid} on server {server}")
        else:
            # Create new record
            cached_image = CachedImage(
                guid=guid,
                server=server,
                image_url=image_url,
                original_url=original_url
            )
            session.add(cached_image)
            logger.info(f"Saved cached image for GUID {guid} on server {server}")
        
        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error saving cached image: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def delete_cached_image(guid: str, server: str) -> bool:
    """
    Delete a cached image from the database.
    
    Args:
        guid: The GUID of the level
        server: The server region
        
    Returns:
        True if successful, False otherwise
    """
    try:
        session = get_session()
        
        deleted = session.query(CachedImage).filter(
            CachedImage.guid == guid,
            CachedImage.server == server
        ).delete()
        
        session.commit()
        
        if deleted:
            logger.info(f"Deleted cached image for GUID {guid} on server {server}")
            return True
        else:
            logger.warning(f"No cached image found for GUID {guid} on server {server}")
            return False
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting cached image: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def delete_all_cached_images() -> int:
    """
    Delete all cached images from the database (cleanup utility).
    
    Returns:
        Number of deleted records
    """
    try:
        session = get_session()
        count = session.query(CachedImage).delete()
        session.commit()
        logger.info(f"Deleted {count} cached images from database")
        return count
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting all cached images: {e}")
        session.rollback()
        return 0
    finally:
        session.close()
