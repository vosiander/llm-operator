import json
from injector import singleton, inject
from loguru import logger
import requests
from typing import Dict, List, Optional, Any
from src.lock_manager import LockManager


class OpenWebUIToolServerException(Exception):
    pass


@singleton
class ToolServerManagement:
    @inject
    def __init__(self, lock_manager: LockManager):
        self.lock_manager = lock_manager

    def ping(self, openwebui_host):
        """Check if Open-WebUI is accessible."""
        try:
            response = requests.get(url=f"{openwebui_host}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to ping Open-WebUI at {openwebui_host}: {e}")
            return False

    def get_tool_servers(self, openwebui_host: str, openwebui_api_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get all tool servers configuration."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/configs/tool_servers",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get tool servers response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                # API returns {"TOOL_SERVER_CONNECTIONS": [...]}
                return data.get("TOOL_SERVER_CONNECTIONS", [])
            else:
                logger.error(f"Failed to get tool servers: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting tool servers: {e}")
            return None

    def get_tool_server_by_url(self, openwebui_host: str, openwebui_api_key: str, url: str) -> Optional[Dict[str, Any]]:
        """Find a tool server by URL."""
        servers = self.get_tool_servers(openwebui_host, openwebui_api_key)
        if servers is None:
            return None
        
        for server in servers:
            if server.get("url") == url:
                return server
        
        logger.info(f"Tool server with URL {url} not found")
        return None

    def create_tool_server(self, openwebui_host: str, openwebui_api_key: str, server_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new tool server to the configuration."""
        server_data = dict(server_data)
        server_data.pop('openwebui_host', None)
        server_data.pop('openwebui_api_key', None)
        server_data.pop('is_installed', None)
        
        # Map CRD field name to API field name
        if 'server_type' in server_data:
            server_data['type'] = server_data.pop('server_type')

        # Use lock to prevent race conditions when multiple servers are created concurrently
        lock_key = f"tool_servers:{openwebui_host}"
        
        with self.lock_manager.acquire_lock(lock_key) as acquired:
            if not acquired:
                raise OpenWebUIToolServerException(f"Failed to acquire lock for {lock_key}")
            
            try:
                # Get current servers
                current_servers = self.get_tool_servers(openwebui_host, openwebui_api_key)
                if current_servers is None:
                    current_servers = []
                
                logger.debug(f"Current tool servers count: {len(current_servers)}")
                
                # Check if already exists
                for server in current_servers:
                    if server.get("url") == server_data.get("url"):
                        logger.info(f"Tool server with URL {server_data.get('url')} already exists")
                        return server
                
                # Add new server
                current_servers.append(server_data)
                logger.debug(f"Adding server, new count: {len(current_servers)}")
                
                logger.trace(f"Creating tool server with data: {json.dumps(server_data, indent=2)}")
                response = requests.post(
                    url=f"{openwebui_host}/api/v1/configs/tool_servers",
                    headers={"Authorization": f"Bearer {openwebui_api_key}"},
                    json={"TOOL_SERVER_CONNECTIONS": current_servers}
                )
                
                logger.trace(f"Create tool server response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"Successfully created tool server {server_data.get('url')}")
                    return server_data
                else:
                    logger.error(f"Failed to create tool server: {response.status_code} - {response.text}")
                    raise OpenWebUIToolServerException(f"Failed to create tool server: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Exception while creating tool server: {e}")
                raise

    def update_tool_server(self, openwebui_host: str, openwebui_api_key: str, url: str, server_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing tool server."""
        server_data = dict(server_data)
        server_data.pop('openwebui_host', None)
        server_data.pop('openwebui_api_key', None)
        server_data.pop('is_installed', None)
        
        # Map CRD field name to API field name
        if 'server_type' in server_data:
            server_data['type'] = server_data.pop('server_type')
        
        # Use lock to prevent race conditions
        lock_key = f"tool_servers:{openwebui_host}"
        
        with self.lock_manager.acquire_lock(lock_key) as acquired:
            if not acquired:
                raise OpenWebUIToolServerException(f"Failed to acquire lock for {lock_key}")
            
            try:
                # Get current servers
                current_servers = self.get_tool_servers(openwebui_host, openwebui_api_key)
                if current_servers is None:
                    raise OpenWebUIToolServerException("Failed to get current tool servers")
                
                # Find and update the server
                found = False
                for i, server in enumerate(current_servers):
                    if server.get("url") == url:
                        current_servers[i] = server_data
                        found = True
                        break
                
                if not found:
                    raise OpenWebUIToolServerException(f"Tool server with URL {url} not found")
                
                # Update servers
                response = requests.post(
                    url=f"{openwebui_host}/api/v1/configs/tool_servers",
                    headers={"Authorization": f"Bearer {openwebui_api_key}"},
                    json={"TOOL_SERVER_CONNECTIONS": current_servers}
                )
                
                logger.trace(f"Update tool server response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"Successfully updated tool server {url}")
                    return server_data
                else:
                    logger.error(f"Failed to update tool server {url}: {response.status_code} - {response.text}")
                    raise OpenWebUIToolServerException(f"Failed to update tool server {url}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Exception while updating tool server {url}: {e}")
                raise

    def delete_tool_server(self, openwebui_host: str, openwebui_api_key: str, url: str) -> bool:
        """Delete a tool server by URL."""
        # Use lock to prevent race conditions
        lock_key = f"tool_servers:{openwebui_host}"
        
        with self.lock_manager.acquire_lock(lock_key) as acquired:
            if not acquired:
                raise OpenWebUIToolServerException(f"Failed to acquire lock for {lock_key}")
            
            try:
                # Get current servers
                current_servers = self.get_tool_servers(openwebui_host, openwebui_api_key)
                if current_servers is None:
                    logger.info("No tool servers found, nothing to delete.")
                    return True
                
                # Filter out the server to delete
                filtered_servers = [s for s in current_servers if s.get("url") != url]
                
                if len(filtered_servers) == len(current_servers):
                    logger.info(f"Tool server with URL {url} does not exist, nothing to delete.")
                    return True
                
                # Update servers
                response = requests.post(
                    url=f"{openwebui_host}/api/v1/configs/tool_servers",
                    headers={"Authorization": f"Bearer {openwebui_api_key}"},
                    json={"TOOL_SERVER_CONNECTIONS": filtered_servers}
                )
                
                logger.trace(f"Delete tool server response: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"Successfully deleted tool server {url}")
                    return True
                else:
                    logger.error(f"Failed to delete tool server {url}: {response.status_code} - {response.text}")
                    raise OpenWebUIToolServerException(f"Failed to delete tool server {url}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Exception while deleting tool server {url}: {e}")
                raise
