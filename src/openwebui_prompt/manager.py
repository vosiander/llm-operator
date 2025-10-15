import json
from injector import singleton
from loguru import logger
import requests
from typing import Dict, List, Optional, Any


class OpenWebUIPromptException(Exception):
    pass


@singleton
class PromptManagement:
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

    def get_prompts(self, openwebui_host: str, openwebui_api_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get all prompts."""
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/prompts/",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get prompts response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get prompts: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting prompts: {e}")
            return None

    def get_prompt_by_command(self, openwebui_host: str, openwebui_api_key: str, command: str) -> Optional[Dict[str, Any]]:
        """Get prompt by command."""
        # Remove "/" prefix for URL if present
        command = command.lstrip('/')
        
        try:
            response = requests.get(
                url=f"{openwebui_host}/api/v1/prompts/command/{command}",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Get prompt by command response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Prompt with command {command} not found: {response.status_code} - {response.text}")
                return None
            else:
                logger.error(f"Failed to get prompt {command}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting prompt {command}: {e}")
            return None

    def create_prompt(self, openwebui_host: str, openwebui_api_key: str, prompt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new prompt."""
        prompt_data = dict(prompt_data)
        prompt_data.pop('openwebui_host', None)
        prompt_data.pop('openwebui_api_key', None)
        prompt_data.pop('is_installed', None)
        
        # Ensure command has "/" prefix for creation
        if 'command' in prompt_data and not prompt_data['command'].startswith('/'):
            prompt_data['command'] = f"/{prompt_data['command']}"
        
        try:
            logger.trace(f"Creating prompt with data: {json.dumps(prompt_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/prompts/create",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=prompt_data
            )
            
            logger.trace(f"Create prompt response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully created prompt {prompt_data.get('command')}")
                return result
            else:
                logger.error(f"Failed to create prompt: {response.status_code} - {response.text}")
                raise OpenWebUIPromptException(f"Failed to create prompt: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Exception while creating prompt: {e}")
            raise

    def update_prompt(self, openwebui_host: str, openwebui_api_key: str, command: str, prompt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing prompt."""
        prompt_data = dict(prompt_data)
        prompt_data.pop('openwebui_host', None)
        prompt_data.pop('openwebui_api_key', None)
        prompt_data.pop('is_installed', None)
        
        # Remove "/" prefix from command for URL if present
        command_for_url = command.lstrip('/')
        
        # Ensure command has "/" prefix in payload for update
        if 'command' in prompt_data and not prompt_data['command'].startswith('/'):
            prompt_data['command'] = f"/{prompt_data['command']}"
        
        try:
            logger.trace(f"Updating prompt {command_for_url} with data: {json.dumps(prompt_data, indent=2)}")
            response = requests.post(
                url=f"{openwebui_host}/api/v1/prompts/command/{command_for_url}/update",
                headers={"Authorization": f"Bearer {openwebui_api_key}"},
                json=prompt_data
            )
            
            logger.trace(f"Update prompt response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully updated prompt {command}")
                return result
            else:
                logger.error(f"Failed to update prompt {command}: {response.status_code} - {response.text}")
                raise OpenWebUIPromptException(f"Failed to update prompt {command}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while updating prompt {command}: {e}")
            raise

    def delete_prompt(self, openwebui_host: str, openwebui_api_key: str, command: str) -> bool:
        """Delete a prompt by command."""
        # Remove "/" prefix for deletion if present
        command = command.lstrip('/')
        
        try:
            response = requests.delete(
                url=f"{openwebui_host}/api/v1/prompts/command/{command}/delete",
                headers={"Authorization": f"Bearer {openwebui_api_key}"}
            )
            
            logger.trace(f"Delete prompt response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted prompt {command}")
                return True
            elif response.status_code == 404:
                logger.info(f"Prompt with command {command} does not exist, nothing to delete.")
                return True
            else:
                logger.error(f"Failed to delete prompt {command}: {response.status_code} - {response.text}")
                raise OpenWebUIPromptException(f"Failed to delete prompt {command}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while deleting prompt {command}: {e}")
            raise

    def upsert_prompt(self, openwebui_host: str, openwebui_api_key: str, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert (create or update) a prompt.
        Checks if the prompt exists by command, then updates if found or creates if not.
        
        Args:
            openwebui_host: The OpenWebUI host URL
            openwebui_api_key: The API key for authentication
            prompt_data: The prompt data to upsert
            
        Returns:
            The created or updated prompt data
        """
        command = prompt_data.get('command')
        if not command:
            raise OpenWebUIPromptException("Command is required for prompt upsert")
        
        # Check if prompt exists
        existing = self.get_prompt_by_command(openwebui_host, openwebui_api_key, command)
        
        if existing:
            logger.info(f"Prompt with command {command} exists, updating...")
            return self.update_prompt(openwebui_host, openwebui_api_key, command, prompt_data)
        
        # Create new prompt
        logger.info(f"Prompt with command {command} does not exist, creating...")
        return self.create_prompt(openwebui_host, openwebui_api_key, prompt_data)
