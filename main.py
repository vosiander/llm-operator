from injector import Injector
from loguru import logger
import kopf
from src.kube.module import KubeModule
import os
import importlib

injector = Injector([KubeModule()])

default_plugins = [
    "litellm_key",
    "litellm_model",
    "n8n_admin_user",
    "n8n_api_key",
    "ollama_model",
]

@kopf.on.startup()
def startup_fn(settings: kopf.OperatorSettings, **kwargs):
    logger.info("Starting llm-operator...")
    logger.debug(f"Operator Settings: {settings}")

    plugins_env = os.getenv("LLM_OPERATOR_PLUGINS", "")
    if not plugins_env:
        plugins_env = ",".join(default_plugins)

    plugins = [plugin.strip() for plugin in plugins_env.split(",") if plugin.strip()]
    
    for plugin_name in plugins:
        try:
            logger.info(f"Loading plugin: {plugin_name}")
            module = importlib.import_module(f"src.{plugin_name}.operator")
            module.register_handlers(injector)
            logger.info(f"Successfully loaded plugin: {plugin_name}")
        except ImportError as e:
            logger.error(f"Failed to import plugin '{plugin_name}': {e}")
        except AttributeError as e:
            logger.error(f"Plugin '{plugin_name}' does not have register_handlers function: {e}")
        except Exception as e:
            logger.error(f"Failed to load plugin '{plugin_name}': {e}")

if __name__ == "__main__":
    logger.error("Do not run this file directly, use `kopf run main.py` instead.")
    exit(1)
