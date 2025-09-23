from injector import Injector
from loguru import logger
import kopf
from src.kube.module import KubeModule
import os

injector = Injector([KubeModule()])

@kopf.on.startup()
def startup_fn(settings: kopf.OperatorSettings, **kwargs):
    logger.info("Starting llm-operator...")
    logger.debug (f"Operator Settings: {settings}")

    if os.getenv("ENABLE_LITELLM_KEY", "true").lower() == "true":
        logger.info("Enabling LiteLLMKey CRD and handlers...")
        import src.litellm_key.operator as litellm_key_operator
        litellm_key_operator.register_handlers(injector)

    if os.getenv("ENABLE_LITELLM_MODEL", "true").lower() == "true":
        logger.info("Enabling LiteLLMModel CRD and handlers...")
        import src.litellm_model.operator as litellm_model_operator
        litellm_model_operator.register_handlers(injector)

    if os.getenv("ENABLE_OLLAMA_MODEL", "true").lower() == "true":
        logger.info("Enabling OllamaModel CRD and handlers...")
        import src.ollama_model.operator as ollama_model_operator
        ollama_model_operator.register_handlers(injector)

if __name__ == "__main__":
    logger.error("Do not run this file directly, use `kopf run main.py` instead.")
    exit(1)