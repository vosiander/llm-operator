import json
from datetime import timezone, datetime

from injector import singleton
from loguru import logger
import requests
import os
from typing import Dict, Optional, Any

class LiteLLMModelException(Exception):
    pass

@singleton
class ModelManagement:
    def __init__(self):
        pass

    def ping(self, litellm_host):
        return requests.get(url=f"{litellm_host}/health/liveness").status_code == 200

    def get_model(self, litellm_host, litellm_api_key, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model information by ID."""
        try:
            response = requests.get(
                url=f"{litellm_host}/models/{model_id}",
                headers={"Authorization": f"Bearer {litellm_api_key}"}
            )
            
            logger.debug(f"Get model response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Model with ID {model_id} not found: {response.status_code} - {response.text}")
                return None
            else:
                logger.error(f"Failed to get model {model_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting model {model_id}: {e}")
            return None

    def get_model_by_name(self, litellm_host, litellm_api_key, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model information by name."""
        try:
            response = requests.get(
                url=f"{litellm_host}/model/info",
                headers={"Authorization": f"Bearer {litellm_api_key}"}
            )
            
            logger.debug(f"List models response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                models_data = response.json()
                # Look for model with matching name
                if "data" in models_data:
                    for model in models_data["data"]:
                        if model.get("id") == model_name or model.get("model_name") == model_name:
                            return model
                logger.info(f"Model with name {model_name} not found")
                return None
            else:
                logger.error(f"Failed to list models: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while getting model by name {model_name}: {e}")
            return None

    def create_model(self, litellm_host, litellm_api_key, model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new model."""
        model_data = dict(model_data)
        if not model_data["model_info"].get("created_at"):
            model_data["model_info"]["created_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if not model_data["model_info"].get("updated_at"):
            model_data["model_info"]["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if not model_data["model_info"].get("created_by"):
            model_data["model_info"]["created_by"] = "genai-operator"

        model_data.pop('litellm_host', None)
        model_data.pop('litellm_api_key', None)

        try:
            logger.debug(f"Creating model with data: {json.dumps(model_data, indent=2)}")
            response = requests.post(
                url=f"{litellm_host}/model/new",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json=model_data
            )
            
            logger.debug(f"Create model response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully created model {model_data.get('model_name')}")
                return response.json()
            else:
                logger.error(f"Failed to create model: {response.status_code} - {response.text}")
                raise LiteLLMModelException(f"Failed to create model: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while creating model: {e}")
            raise

    def update_model(self, litellm_host, litellm_api_key, model_id: str, model_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        model_data.pop('litellm_host', None)
        model_data.pop('litellm_api_key', None)
        """Update an existing model."""
        try:
            model_data["id"] = model_id
            
            response = requests.post(
                url=f"{litellm_host}/model/update",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json=dict(model_data)
            )
            
            logger.debug(f"Update model response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully updated model {model_id}")
                return response.json()
            else:
                logger.error(f"Failed to update model {model_id}: {response.status_code} - {response.text}")
                raise LiteLLMModelException(f"Failed to update model {model_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while updating model {model_id}: {e}")
            raise LiteLLMModelException(f"Exception while updating model {model_id}: {e}")

    def delete_model_by_name(self, litellm_host, litellm_api_key, model_name: str) -> bool:
        model = self.get_model_by_name(litellm_host, litellm_api_key, model_name)
        if model is None:
            logger.info(f"Model with name {model_name} does not exist, nothing to delete.")
            return True

        if model["model_info"].get("id") is None:
            logger.error(f"Model with name {model_name} has no ID, cannot delete.")
            raise LiteLLMModelException("Model has no ID, cannot delete.")

        logger.debug(f"Deleting model {model_name} with ID {model["model_info"].get('id')} and data: {json.dumps(model, indent=2)}")
        return self.delete_model(litellm_host, litellm_api_key, model["model_info"].get("id"))

    def delete_model(self, litellm_host, litellm_api_key, model_id: str) -> bool:
        """Delete a model by ID."""
        try:
            response = requests.post(
                url=f"{litellm_host}/model/delete",
                headers={"Authorization": f"Bearer {litellm_api_key}"},
                json={"id": model_id}
            )
            
            logger.debug(f"Delete model response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted model {model_id}")
                return True
            else:
                logger.error(f"Failed to delete model {model_id}: {response.status_code} - {response.text}")
                raise ValueError(f"Failed to delete model {model_id}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while deleting model {model_id}: {e}")
            raise
