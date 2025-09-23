from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.litellm_model.manager import ModelManagement
from src.litellm_model.crd import LiteLLMModel

injector: Injector = None
api: ApiClient = None

def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering LiteLLMModel handlers...")
    LiteLLMModel.install(api, exist_ok=True)

@kopf.on.timer("ops.veitosiander.de", "v1", "LiteLLMModel", interval=30)
def timer_fn(spec, name, namespace, **kwargs):
    if not spec.get('is_installed', False):
        logger.warning(f"model not installed for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging LiteLLM service...")
    model_management = injector.get(ModelManagement)
    if not model_management.ping(spec['litellm_host']):
        logger.error("Failed to ping LiteLLM service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling LiteLLMModel resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("LiteLLMModel.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    model = model_management.get_model_by_name(spec['litellm_host'], spec['litellm_api_key'], spec['model_name'])
    if model is not None:
        logger.info(f"Model {spec['model_name']} exists. Nothing to do...")
    else:
        logger.warning(f"Model {spec['model_name']} does not exist. Recreating...")
        model_management.create_model(spec['litellm_host'], spec['litellm_api_key'], spec)
        logger.info(f"Recreated modeö for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "LiteLLMModel")
def delete_fn(spec, name, namespace, **kwargs):
    model_management = injector.get(ModelManagement)

    logger.info(f"Deleting LiteLLM resource: {namespace}/{name} with spec: {spec}")
    try:
        model_management.delete_model_by_name(spec['litellm_host'], spec['litellm_api_key'], spec['model_name'])
        logger.info(f"LiteLLMModel {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete model {spec['model_name']}: {e}")
        pass

@kopf.on.create("ops.veitosiander.de", "v1", "LiteLLMModel")
def create_fn(spec, name, namespace,**kwargs):
    model_management = injector.get(ModelManagement)

    logger.info(f"Creating LiteLLM resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("LiteLLMModel.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        model = model_management.get_model_by_name(spec['litellm_host'], spec['litellm_api_key'], spec['model_name'])
        if model is not None:
            logger.warning(f"Model with name {spec['model_name']} already exists. Skipping...")
            return {"status": "created"}

        logger.info(f"Creating new model {spec['model_name']}...")
        model = model_management.create_model(spec['litellm_host'], spec['litellm_api_key'], spec)
        logger.info(f"Created model for {namespace}/{name} with {model.get("model_name", "no-model-name")}, updating CRD...")
        cr.patch({"spec": {"is_installed": True}})

        logger.info(f"LiteLLMModel {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create model for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create model: {e}", delay=30)

    return {"status": "created"}