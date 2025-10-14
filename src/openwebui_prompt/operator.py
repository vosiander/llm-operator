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


@kopf.on.timer("ops.veitosiander.de", "v1", "OpenWebUIPrompt", interval=30)
def timer_fn(spec, name, namespace, **kwargs):
    if not spec.get('is_installed', False):
        logger.warning(f"prompt not installed for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    prompt_management = injector.get(PromptManagement)
    if not prompt_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIPrompt resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIPrompt.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    prompt = prompt_management.get_prompt_by_command(spec['openwebui_host'], spec['openwebui_api_key'], spec['command'])
    if prompt is not None:
        logger.info(f"Prompt {spec['command']} exists. Nothing to do...")
        return

    logger.warning(f"Cannot confirm prompt {spec['command']} status. Trying update first...")
    try:
        prompt_management.update_prompt(spec['openwebui_host'], spec['openwebui_api_key'], spec['command'], spec)
        logger.info(f"Successfully updated existing prompt {spec['command']}")
    except Exception as update_error:
        logger.info(f"Update failed, prompt likely doesn't exist (error: {update_error}). Creating prompt {spec['command']}...")
        try:
            prompt_management.create_prompt(spec['openwebui_host'], spec['openwebui_api_key'], spec)
            logger.info(f"Successfully created prompt for {namespace}/{name}")
        except Exception as create_error:
            logger.error(f"Failed to create prompt after update failed: {create_error}")
            raise kopf.TemporaryError(f"Failed to create prompt: {create_error}", delay=30)


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def delete_fn(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)

    logger.info(f"Deleting OpenWebUIPrompt resource: {namespace}/{name} with spec: {spec}")
    try:
        prompt_management.delete_prompt(spec['openwebui_host'], spec['openwebui_api_key'], spec['command'])
        logger.info(f"OpenWebUIPrompt {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete prompt {spec['command']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIPrompt")
def create_fn(spec, name, namespace, **kwargs):
    prompt_management = injector.get(PromptManagement)

    logger.info(f"Creating OpenWebUIPrompt resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("OpenWebUIPrompt.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        prompt = prompt_management.get_prompt_by_command(spec['openwebui_host'], spec['openwebui_api_key'], spec['command'])
        if prompt is not None:
            logger.warning(f"Prompt with command {spec['command']} already exists. Skipping...")
            return {"status": "created"}

        logger.info(f"Creating new prompt {spec['command']}...")
        prompt = prompt_management.create_prompt(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Created prompt for {namespace}/{name} with command {prompt.get('command', 'no-command')}, updating CRD...")
        cr.patch({"spec": {"is_installed": True}})

        logger.info(f"OpenWebUIPrompt {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create prompt for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create prompt: {e}", delay=30)

    return {"status": "created"}
