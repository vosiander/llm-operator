from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.openwebui_prompt.manager import PromptManagement
from src.openwebui_prompt.crd import OpenWebUIPrompt

injector: Injector = None
api: ApiClient = None


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering OpenWebUIPrompt handlers...")
    OpenWebUIPrompt.install(api, exist_ok=True)


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def delete_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    prompt_management = injector.get(PromptManagement)

    logger.info(f"Deleting OpenWebUIPrompt resource: {namespace}/{name} with spec: {spec}")
    try:
        prompt_management.delete_prompt(spec['openwebui_host'], spec['openwebui_api_key'], spec['command'])
        logger.info(f"OpenWebUIPrompt {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete prompt {spec['command']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def upsert_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    prompt_management = injector.get(PromptManagement)
    
    logger.info(f"Upserting OpenWebUIPrompt resource: {namespace}/{name}")
    
    try:
        prompt = prompt_management.upsert_prompt(
            spec['openwebui_host'],
            spec['openwebui_api_key'],
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIPrompt.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIPrompt {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert prompt for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert prompt: {e}", delay=30)
