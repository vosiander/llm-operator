import json
from injector import singleton
from loguru import logger
import requests
from typing import Dict, List, Optional, Any


class OpenWebUIChannelException(Exception):
    pass


@singleton
class ChannelManagement:
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

    def get_channels(self, openwebui_host: str, openwebui_api_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get all channels."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/channels/",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get channels response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get channels: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting channels: {e}")
            return None

    def get_channel_by_id(self, openwebui_host: str, openwebui_api_key: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel by ID."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/channels/{channel_id}",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get channel by ID response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Channel with ID {channel_id} not found: {response.status_code} - {response.text}")
                return None
            else:
                logger.error(f"Failed to get channel {channel_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting channel {channel_id}: {e}")
            return None

    def get_channel_by_name(self, openwebui_host: str, openwebui_api_key: str, name: str) -> Optional[Dict[str, Any]]:
        """Find channel by name."""
        channels = self.get_channels(openwebui_host, openwebui_api_key)
        if channels is None:
            return None
        
        for channel in channels:
            if channel.get("name") == name:
                return channel
        
        logger.info(f"Channel with name {name} not found")
        return None

    def create_channel(self, openwebui_host: str, openwebui_api_key: str, channel_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new channel."""
        channel_data = dict(channel_data)
        channel_data.pop('openwebui_host', None)
        channel_data.pop('openwebui_api_key', None)
        channel_data.pop('is_installed', None)
        channel_data.pop('channel_id', None)
        
        try:
            logger.trace(f"Creating channel with data: {json.dumps(channel_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/channels/create",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=channel_data
            )
            
            logger.trace(f"Create channel response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully created channel {channel_data.get('name')} with ID {result.get('id')}")
                return result
            else:
                logger.error(f"Failed to create channel: {response.status_code} - {response.text}")
                raise OpenWebUIChannelException(f"Failed to create channel: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while creating channel: {e}")
            raise

    def update_channel(self, openwebui_host: str, openwebui_api_key: str, channel_id: str, channel_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing channel."""
        channel_data = dict(channel_data)
        channel_data.pop('openwebui_host', None)
        channel_data.pop('openwebui_api_key', None)
        channel_data.pop('is_installed', None)
        channel_data.pop('channel_id', None)
        
        try:
            logger.trace(f"Updating channel {channel_id} with data: {json.dumps(channel_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/channels/{channel_id}/update",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=channel_data
            )
            
            logger.trace(f"Update channel response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully updated channel {channel_id}")
                return result
            else:
                logger.error(f"Failed to update channel {channel_id}: {response.status_code} - {response.text}")
                raise OpenWebUIChannelException(f"Failed to update channel {channel_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while updating channel {channel_id}: {e}")
            raise

    def delete_channel(self, openwebui_host: str, openwebui_api_key: str, channel_id: str) -> bool:
        """Delete a channel by ID."""
        try:
            response = requests.delete(
                url=f"{openwebui_host}/api/v1/channels/{channel_id}/delete",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Delete channel response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted channel {channel_id}")
                return True
            else:
                logger.error(f"Failed to delete channel {channel_id}: {response.status_code} - {response.text}")
                raise OpenWebUIChannelException(f"Failed to delete channel {channel_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while deleting channel {channel_id}: {e}")
            raise

    def delete_channel_by_name(self, openwebui_host: str, openwebui_api_key: str, name: str) -> bool:
        """Delete a channel by name."""
        channel = self.get_channel_by_name(openwebui_host, openwebui_api_key, name)
        if channel is None:
            logger.info(f"Channel with name {name} does not exist, nothing to delete.")
            return True

        channel_id = channel.get('id')
        if not channel_id:
            logger.error(f"Channel with name {name} has no ID, cannot delete.")
            raise OpenWebUIChannelException("Channel has no ID, cannot delete.")

        logger.info(f"Deleting channel {name} with ID {channel_id}")
        return self.delete_channel(openwebui_host, openwebui_api_key, channel_id)
