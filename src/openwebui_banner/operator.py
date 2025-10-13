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
    if not spec.get('is_installed', False):
        logger.warning(f"banner not installed for {namespace}/{name}, skipping reconciliation.")
        return

    logger.info("Pinging Open-WebUI service...")
    banner_management = injector.get(BannerManagement)
    if not banner_management.ping(spec['openwebui_host']):
        logger.error("Failed to ping Open-WebUI service. Will retry in the next interval.")
        return

    logger.info(f"Reconciling OpenWebUIBanner resource: {namespace}/{name} with spec: {spec}")
    cr = list(kr8s.get("OpenWebUIBanner.ops.veitosiander.de", name, namespace=namespace))[0]

    logger.info(f"Fetched CR: {cr} <- {name}")
    banner = banner_management.get_banner_by_id(spec['openwebui_host'], spec['openwebui_api_key'], spec['id'])
    if banner is not None:
        logger.info(f"Banner {spec['id']} exists. Nothing to do...")
    else:
        logger.warning(f"Banner {spec['id']} does not exist. Recreating...")
        banner_management.create_banner(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Recreated banner for {namespace}/{name}")


@kopf.on.delete("ops.veitosiander.de", "v1", "OpenWebUIBanner")
def delete_fn(spec, name, namespace, **kwargs):
    banner_management = injector.get(BannerManagement)

    logger.info(f"Deleting OpenWebUIBanner resource: {namespace}/{name} with spec: {spec}")
    try:
        banner_management.delete_banner(spec['openwebui_host'], spec['openwebui_api_key'], spec['id'])
        logger.info(f"OpenWebUIBanner {namespace}/{name} deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete banner {spec['id']}: {e}")
        pass


@kopf.on.create("ops.veitosiander.de", "v1", "OpenWebUIBanner")
def create_fn(spec, name, namespace, **kwargs):
    banner_management = injector.get(BannerManagement)

    logger.info(f"Creating OpenWebUIBanner resource: {namespace}/{name} with spec: {spec}")

    cr = list(kr8s.get("OpenWebUIBanner.ops.veitosiander.de", name, namespace=namespace))[0]
    logger.info(f"Fetched CR: {cr}")

    try:
        banner = banner_management.get_banner_by_id(spec['openwebui_host'], spec['openwebui_api_key'], spec['id'])
        if banner is not None:
            logger.warning(f"Banner with ID {spec['id']} already exists. Skipping...")
            return {"status": "created"}

        logger.info(f"Creating new banner {spec['id']}...")
        banner = banner_management.create_banner(spec['openwebui_host'], spec['openwebui_api_key'], spec)
        logger.info(f"Created banner for {namespace}/{name} with ID {banner.get('id', 'no-id')}, updating CRD...")
        cr.patch({"spec": {"is_installed": True}})

        logger.info(f"OpenWebUIBanner {namespace}/{name} created successfully.")
    except Exception as e:
        logger.error(f"Failed to create banner for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to create banner: {e}", delay=30)

    return {"status": "created"}
