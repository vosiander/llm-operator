from injector import singleton
from loguru import logger
import requests
import os

@singleton
class ModelManagement:
    def __init__(self):
        self.pull_timeout = int(os.getenv("OLLAMA_PULL_TIMEOUT", "600"))
        pass

    def get_model(self, ollama_host: str, name: str, tag: str):
        """Get model information from Ollama API"""
        try:
            url = f"{ollama_host}/api/show"
            payload = {"model": f"{name}:{tag}"}
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Successfully retrieved model info for {name}")
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Model {name} not found")
                return None
            else:
                logger.error(f"Failed to get model {name}: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to Ollama at {ollama_host}: {e}")
            return None

    def delete_model(self, ollama_host: str, name: str, tag: str):
        """Delete a model from Ollama"""
        try:
            url = f"{ollama_host}/api/delete"
            payload = {"model": f"{name}:{tag}"}
            response = requests.delete(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted model {name}")
                return True
            elif response.status_code == 404:
                logger.warning(f"Model {name} not found for deletion")
                return True
            else:
                logger.error(f"Failed to delete model {name}: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to Ollama at {ollama_host}: {e}")
            return False

    def pull_model(self, ollama_host: str, name: str, tag: str):
        """Pull a model from Ollama registry"""
        try:
            # Format model name with tag
            model_name = f"{name}:{tag}"
            
            url = f"{ollama_host}/api/pull"
            payload = {"model": model_name, "stream": False}
            response = requests.post(url, json=payload, timeout=self.pull_timeout)  # Longer timeout for model downloads
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    logger.info(f"Successfully pulled model {model_name}")
                    return True
                else:
                    logger.error(f"Failed to pull model {model_name}: {result}")
                    return False
            else:
                logger.error(f"Failed to pull model {model_name}: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to Ollama at {ollama_host}: {e}")
            return False
