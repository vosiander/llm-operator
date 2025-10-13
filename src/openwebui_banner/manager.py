import json
from injector import singleton
from loguru import logger
import requests
from typing import Dict, List, Optional, Any


class OpenWebUIBannerException(Exception):
    pass


@singleton
class BannerManagement:
    def __init__(self):
        pass

    def ping(self, openwebui_host):
        """Check if Open-WebUI is accessible."""
        try:
            response = requests.get(url=f"{openwebui_host}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to ping Open-WebUI at {openwebui_host}: {e}")
            return False

    def get_banners(self, openwebui_host: str, openwebui_api_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get all banners."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/configs/banners",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get banners response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                return data.get("banners", []) if isinstance(data, dict) else []
            else:
                logger.error(f"Failed to get banners: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting banners: {e}")
            return None

    def get_banner_by_id(self, openwebui_host: str, openwebui_api_key: str, banner_id: str) -> Optional[Dict[str, Any]]:
        """Find a banner by ID."""
        banners = self.get_banners(openwebui_host, openwebui_api_key)
        if banners is None:
            return None
        
        for banner in banners:
            if banner.get("id") == banner_id:
                return banner
        
        logger.info(f"Banner with ID {banner_id} not found")
        return None

    def create_banner(self, openwebui_host: str, openwebui_api_key: str, banner_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new banner to the configuration."""
        banner_data = dict(banner_data)
        banner_data.pop('openwebui_host', None)
        banner_data.pop('openwebui_api_key', None)
        banner_data.pop('is_installed', None)
        
        try:
            # Get current banners
            current_banners = self.get_banners(openwebui_host, openwebui_api_key)
            if current_banners is None:
                current_banners = []
            
            # Check if already exists
            for banner in current_banners:
                if banner.get("id") == banner_data.get("id"):
                    logger.info(f"Banner with ID {banner_data.get('id')} already exists")
                    return banner
            
            # Add new banner
            current_banners.append(banner_data)
            
            logger.trace(f"Creating banner with data: {json.dumps(banner_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/configs/banners",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json={"banners": current_banners}
            )
            
            logger.trace(f"Create banner response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully created banner {banner_data.get('id')}")
                return banner_data
            else:
                logger.error(f"Failed to create banner: {response.status_code} - {response.text}")
                raise OpenWebUIBannerException(f"Failed to create banner: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while creating banner: {e}")
            raise

    def update_banner(self, openwebui_host: str, openwebui_api_key: str, banner_id: str, banner_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing banner."""
        banner_data = dict(banner_data)
        banner_data.pop('openwebui_host', None)
        banner_data.pop('openwebui_api_key', None)
        banner_data.pop('is_installed', None)
        
        try:
            # Get current banners
            current_banners = self.get_banners(openwebui_host, openwebui_api_key)
            if current_banners is None:
                raise OpenWebUIBannerException("Failed to get current banners")
            
            # Find and update the banner
            found = False
            for i, banner in enumerate(current_banners):
                if banner.get("id") == banner_id:
                    current_banners[i] = banner_data
                    found = True
                    break
            
            if not found:
                raise OpenWebUIBannerException(f"Banner with ID {banner_id} not found")
            
            # Update banners
            response = requests.post(
                url=f"{openwebui_host}/api/v1/configs/banners",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json={"banners": current_banners}
            )
            
            logger.trace(f"Update banner response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully updated banner {banner_id}")
                return banner_data
            else:
                logger.error(f"Failed to update banner {banner_id}: {response.status_code} - {response.text}")
                raise OpenWebUIBannerException(f"Failed to update banner {banner_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while updating banner {banner_id}: {e}")
            raise

    def delete_banner(self, openwebui_host: str, openwebui_api_key: str, banner_id: str) -> bool:
        """Delete a banner by ID."""
        try:
            # Get current banners
            current_banners = self.get_banners(openwebui_host, openwebui_api_key)
            if current_banners is None:
                logger.info("No banners found, nothing to delete.")
                return True
            
            # Filter out the banner to delete
            filtered_banners = [b for b in current_banners if b.get("id") != banner_id]
            
            if len(filtered_banners) == len(current_banners):
                logger.info(f"Banner with ID {banner_id} does not exist, nothing to delete.")
                return True
            
            # Update banners
            response = requests.post(
                url=f"{openwebui_host}/api/v1/configs/banners",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json={"banners": filtered_banners}
            )
            
            logger.trace(f"Delete banner response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted banner {banner_id}")
                return True
            else:
                logger.error(f"Failed to delete banner {banner_id}: {response.status_code} - {response.text}")
                raise OpenWebUIBannerException(f"Failed to delete banner {banner_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while deleting banner {banner_id}: {e}")
            raise
