from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import os

from src.ollama_model.manager import ModelManagement
from src.ollama_model.crd import OllamaModel

injector: Injector = None
api: ApiClient = None

def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering OllamaModel handlers...")
    OllamaModel.install(api, exist_ok=True)

@kopf.on.timer("ops.veitosiander.de", "v1", "OllamaModel", interval=os.getenv("LLM_OPERATOR_RECONCILE_INTERVAL", 600))
def timer_fn(spec, name, namespace, **kwargs):
    if not spec.get('model') or not spec.get('ollama_host'):
        logger.warning(f"Model or ollama_host not specified for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info(f"Reconciling OllamaModel resource: {namespace}/{name}")
    model_management = injector.get(ModelManagement)
    
    # Check if model exists on Ollama server
    model_info = model_management.get_model(spec['ollama_host'], spec['model'], spec['tag'])
    if model_info is not None:
        logger.info(f"Model {spec['model']} exists on Ollama server. Nothing to do...")
    else:
        logger.info(f"Model {spec['model']} does not exist. Pulling model...")
        success = model_management.pull_model(spec['ollama_host'], spec['model'], spec.get('tag', 'latest'))
        if success:
            logger.info(f"Successfully pulled model {spec['model']} for {namespace}/{name}")
        else:
            logger.error(f"Failed to pull model {spec['model']} for {namespace}/{name}")

@kopf.on.delete("ops.veitosiander.de", "v1", "OllamaModel")
def delete_fn(spec, name, namespace, **kwargs):
    model_management = injector.get(ModelManagement)

    logger.info(f"Deleting OllamaModel resource: {namespace}/{name}")
    try:
        success = model_management.delete_model(spec['ollama_host'], spec['model'], spec['tag'])
        if success:
            logger.info(f"OllamaModel {namespace}/{name} deleted successfully.")
        else:
            logger.warning(f"Model {spec['model']} was not found on server, but CRD will be deleted anyway.")
    except Exception as e:
        logger.error(f"Failed to delete model {spec['model']}: {e}")

@kopf.on.update("ops.veitosiander.de", "v1", "OllamaModel")
@kopf.on.create("ops.veitosiander.de", "v1", "OllamaModel")
def create_fn(spec, name, namespace, **kwargs):
    model_management = injector.get(ModelManagement)

    logger.info(f"Creating OllamaModel resource: {namespace}/{name}")

    try:
        # Check if model already exists
        model_info = model_management.get_model(spec['ollama_host'], spec['model'], spec['tag'])
        if model_info is not None:
            logger.info(f"Model {spec['model']} already exists on Ollama server. Nothing to do.")
            return {"status": "created"}

        # Pull the model
        logger.info(f"Pulling model {spec['model']}:{spec.get('tag', 'latest')}...")
        success = model_management.pull_model(spec['ollama_host'], spec['model'], spec.get('tag', 'latest'))
        
        if success:
            logger.info(f"OllamaModel {namespace}/{name} created successfully.")
            return {"status": "created"}
        else:
            raise Exception(f"Failed to pull model {spec['model']}")
            
    except Exception as e:
        logger.error(f"Failed to create model for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create model: {e}", delay=30)
