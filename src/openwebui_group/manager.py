import json
from injector import singleton
from loguru import logger
import requests
from typing import Dict, List, Optional, Any


class OpenWebUIGroupException(Exception):
    pass


@singleton
class GroupManagement:
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

    def get_groups(self, openwebui_host: str, openwebui_api_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get all groups."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/groups/",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get groups response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get groups: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting groups: {e}")
            return None

    def get_group_by_id(self, openwebui_host: str, openwebui_api_key: str, group_id: str) -> Optional[Dict[str, Any]]:
        """Get group by ID."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/groups/id/{group_id}",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get group by ID response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Group with ID {group_id} not found: {response.status_code} - {response.text}")
                return None
            else:
                logger.error(f"Failed to get group {group_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting group {group_id}: {e}")
            return None

    def get_group_by_name(self, openwebui_host: str, openwebui_api_key: str, name: str) -> Optional[Dict[str, Any]]:
        """Find group by name."""
        groups = self.get_groups(openwebui_host, openwebui_api_key)
        if groups is None:
            return None
        
        for group in groups:
            if group.get("name") == name:
                return group
        
        logger.info(f"Group with name {name} not found")
        return None

    def create_group(self, openwebui_host: str, openwebui_api_key: str, group_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new group."""
        group_data = dict(group_data)
        group_data.pop('openwebui_host', None)
        group_data.pop('openwebui_api_key', None)
        group_data.pop('is_installed', None)
        group_data.pop('group_id', None)
        
        try:
            logger.trace(f"Creating group with data: {json.dumps(group_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/groups/create",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=group_data
            )
            
            logger.trace(f"Create group response: {response.status_code} - {response.text}")
            
            if response.status_code != 200:
                logger.error(f"Failed to create group: {response.status_code} - {response.text}")
                raise OpenWebUIGroupException(f"Failed to create group: {response.status_code} - {response.text}")

            result = response.json()
            logger.info(f"Successfully created group {group_data.get('name')} with ID {result.get('id')}")

            logger.trace(f"Adding users to group: {json.dumps(group_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/groups/id/{result.get('id')}/users/add",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=group_data
            )

            if response.status_code != 200:
                logger.error(f"Failed to add users to group: {response.status_code} - {response.text}")
                raise OpenWebUIGroupException(f"Failed to create group: {response.status_code} - {response.text}")

            logger.info(f"Successfully added users to group {group_data.get('name')}")
            return result

                
        except Exception as e:
            logger.error(f"Exception while creating group: {e}")
            raise

    def update_group(self, openwebui_host: str, openwebui_api_key: str, group_id: str, group_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing group."""
        group_data = dict(group_data)
        group_data.pop('openwebui_host', None)
        group_data.pop('openwebui_api_key', None)
        group_data.pop('is_installed', None)
        group_data.pop('group_id', None)
        
        try:
            logger.trace(f"Updating group {group_id} with data: {json.dumps(group_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/groups/id/{group_id}/update",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=group_data
            )
            
            logger.trace(f"Update group response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully updated group {group_id}")
                return result
            else:
                logger.error(f"Failed to update group {group_id}: {response.status_code} - {response.text}")
                raise OpenWebUIGroupException(f"Failed to update group {group_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while updating group {group_id}: {e}")
            raise

    def delete_group(self, openwebui_host: str, openwebui_api_key: str, group_id: str) -> bool:
        """Delete a group by ID."""
        try:
            response = requests.delete(
                url=f"{openwebui_host}/api/v1/groups/id/{group_id}/delete",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Delete group response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted group {group_id}")
                return True
            else:
                logger.error(f"Failed to delete group {group_id}: {response.status_code} - {response.text}")
                raise OpenWebUIGroupException(f"Failed to delete group {group_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while deleting group {group_id}: {e}")
            raise

    def delete_group_by_name(self, openwebui_host: str, openwebui_api_key: str, name: str) -> bool:
        """Delete a group by name."""
        group = self.get_group_by_name(openwebui_host, openwebui_api_key, name)
        if group is None:
            logger.info(f"Group with name {name} does not exist, nothing to delete.")
            return True

        group_id = group.get('id')
        if not group_id:
            logger.error(f"Group with name {name} has no ID, cannot delete.")
            raise OpenWebUIGroupException("Group has no ID, cannot delete.")

        logger.info(f"Deleting group {name} with ID {group_id}")
        return self.delete_group(openwebui_host, openwebui_api_key, group_id)

    def upsert_group(self, openwebui_host: str, openwebui_api_key: str, group_data: Dict[str, Any], group_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upsert (create or update) a group.
        Checks if the group exists by ID or name, then updates if found or creates if not.
        
        Args:
            openwebui_host: The OpenWebUI host URL
            openwebui_api_key: The API key for authentication
            group_data: The group data to upsert
            group_id: Optional group ID to check first
            
        Returns:
            The created or updated group data
        """
        # Try by ID first if provided
        if group_id:
            existing = self.get_group_by_id(openwebui_host, openwebui_api_key, group_id)
            if existing:
                logger.info(f"Group with ID {group_id} exists, updating...")
                return self.update_group(openwebui_host, openwebui_api_key, group_id, group_data)
        
        # Check by name
        group_name = group_data.get('name')
        if group_name:
            existing = self.get_group_by_name(openwebui_host, openwebui_api_key, group_name)
            if existing:
                logger.info(f"Group with name {group_name} exists, updating...")
                return self.update_group(openwebui_host, openwebui_api_key, existing['id'], group_data)
        
        # Create new group
        logger.info(f"Group does not exist, creating new group...")
        return self.create_group(openwebui_host, openwebui_api_key, group_data)
