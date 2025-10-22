from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.litellm_key.crd import LiteLLMKey
from src.litellm_key.manager import KeyManagement

injector: Injector = None
api: ApiClient = None

def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering LiteLLMKey handlers...")
    LiteLLMKey.install(api, exist_ok=True)


@kopf.on.delete("ops.veitosiander.de", "v1", "LiteLLMKey")
def delete_fn(spec, name, namespace, **kwargs):
    litellm_key_management = injector.get(KeyManagement)

    logger.info(f"Deleting LiteLLM resource: {namespace}/{name} with spec: {spec}")
    try:
        litellm_key_management.delete_key(spec["litellm_host"], spec["litellm_api_key"], spec['key_alias'])
        logger.info(f"LiteLLMKey {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete key with alias {spec['key_alias']}: {e}")
        pass


@kopf.on.update("ops.veitosiander.de", "v1", "LiteLLMKey")
@kopf.on.create("ops.veitosiander.de", "v1", "LiteLLMKey")
def create_fn(spec, name, namespace, **kwargs):
    litellm_key_management = injector.get(KeyManagement)

    logger.info(f"Creating LiteLLM resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("LiteLLMKey.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        key = litellm_key_management.get_key_by_alias(spec["litellm_host"], spec["litellm_api_key"], spec['key_alias'])
        if key is not None:
            logger.warning(
                f"Key for host {spec['litellm_host']} alias {spec['key_alias']} already exists for user {spec['user_id']}. Deleting key...")
            litellm_key_management.delete_key(spec["litellm_host"], spec["litellm_api_key"], spec['key_alias'])

        logger.info(f"Generating new key for user {spec['user_id']} with alias {spec['key_alias']}...")
        key = litellm_key_management.generate_key(
            spec["litellm_host"],
            spec["litellm_api_key"],
            user_id=spec['user_id'],
            team_id=spec.get('team_id', ""),
            key_alias=spec['key_alias'],
            key_name=spec["key_name"],
        )
        logger.info(f"Generated key for {namespace}/{name}, updating CRD...")
        cr.patch({"spec": {"key_value": key}})

        logger.info(f"LiteLLMKey {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create key for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create key: {e}", delay=30)

    return {"status": "created"}
