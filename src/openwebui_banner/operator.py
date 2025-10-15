from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s

from src.openwebui_banner.manager import BannerManagement
from src.openwebui_banner.crd import OpenWebUIBanner

injector: Injector = None
api: ApiClient = None


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering OpenWebUIBanner handlers...")
    OpenWebUIBanner.install(api, exist_ok=True)

@kopf.on.timer("ops.veitosiander.de", "v1", "OpenWebUIBanner", interval=30)
def timer_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.debug(f"No API key for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    banner_management = injector.get(BannerManagement)
    if not banner_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIBanner resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIBanner.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    banner = banner_management.upsert_banner(spec['openwebui_host'], spec['openwebui_api_key'], spec)
    logger.info(f"Upserted banner {spec['id']} for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIBanner")
def delete_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, nothing to delete.")
        return
    
    banner_management = injector.get(BannerManagement)

    logger.info(f"Deleting OpenWebUIBanner resource: {namespace}/{name} with spec: {spec}")
    try:
        banner_management.delete_banner(spec['openwebui_host'], spec['openwebui_api_key'], spec['id'])
        logger.info(f"OpenWebUIBanner {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete banner {spec['id']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIBanner")
@kopf.on.update("ops.veitosiander.de", "v1", "OpenWebUIBanner")
def upsert_fn(spec, name, namespace, **kwargs):
    api_key = spec.get('openwebui_api_key', '').strip()
    
    if not api_key:
        logger.info(f"No API key for {namespace}/{name}, skipping upsert.")
        return {"status": "waiting_for_api_key"}
    
    banner_management = injector.get(BannerManagement)
    
    logger.info(f"Upserting OpenWebUIBanner resource: {namespace}/{name}")
    
    try:
        banner = banner_management.upsert_banner(
            spec['openwebui_host'],
            spec['openwebui_api_key'],
            spec
        )
        
        # Update is_installed flag if needed
        if not spec.get('is_installed', False):
            cr = list(kr8s.get("OpenWebUIBanner.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({"spec": {"is_installed": True}})
        
        logger.info(f"OpenWebUIBanner {namespace}/{name} upserted successfully.")
        return {"status": "upserted"}
    except Exception as e:
        logger.error(f"Failed to upsert banner for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to upsert banner: {e}", delay=30)
