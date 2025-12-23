"""Utility functions for generating slugs."""

import re
from datetime import datetime


def email_to_slug(email: str) -> str:
    """Convert email address to a filesystem-safe slug.
    
    Args:
        email: Email address (e.g., "user@example.com")
        
    Returns:
        Slug string (e.g., "user-example-com")
    """
    # Remove everything except alphanumeric, dots, and @
    # Replace @ with dash
    slug = email.lower().strip()
    slug = slug.replace("@", "-")
    slug = slug.replace(".", "-")
    
    # Remove any characters that aren't alphanumeric or dash
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    
    # Remove multiple consecutive dashes
    slug = re.sub(r"-+", "-", slug)
    
    # Remove leading/trailing dashes
    slug = slug.strip("-")
    
    return slug


def name_to_slug(name: str) -> str:
    """Convert a name to a filesystem-safe slug.
    
    Args:
        name: Name string (e.g., "Max the Dog")
        
    Returns:
        Slug string (e.g., "max-the-dog")
    """
    # Convert to lowercase
    slug = name.lower().strip()
    
    # Replace spaces and special characters with dashes
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)
    slug = slug.replace(" ", "-")
    
    # Remove multiple consecutive dashes
    slug = re.sub(r"-+", "-", slug)
    
    # Remove leading/trailing dashes
    slug = slug.strip("-")
    
    # Limit length to avoid issues with filesystem
    if len(slug) > 50:
        slug = slug[:50]
    
    return slug


def get_user_backup_dir(base_dir: str, email: str) -> str:
    """Get backup directory path for a user based on email.
    
    Args:
        base_dir: Base directory for backups
        email: User email address
        
    Returns:
        Full path to user's backup directory
    """
    slug = email_to_slug(email)
    return f"{base_dir}/{slug}"


def get_unique_order_dir(base_dir: str, email: str, pet_name: str, timestamp: str = None) -> str:
    """Get a unique directory path for an order.
    
    Creates a unique directory per order with format:
    base_dir/[email-slug]/[pet-name-slug]_[timestamp]/
    
    Args:
        base_dir: Base directory for backups (e.g., "temp")
        email: User email address
        pet_name: Pet's name
        timestamp: Optional timestamp string (YYYYMMDD_HHMMSS format).
                   If None, generates current timestamp.
        
    Returns:
        Full path to unique order directory
    """
    email_slug = email_to_slug(email)
    pet_slug = name_to_slug(pet_name)
    
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    order_dir = f"{pet_slug}_{timestamp}"
    
    return f"{base_dir}/{email_slug}/{order_dir}"

