from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.uptime_kuma_monitor.manager import MonitorManagement
from src.uptime_kuma_monitor.crd import UptimeKumaMonitor

injector: Injector = None
api: ApiClient = None


def get_credentials_from_secret(secret_name: str, secret_namespace: str) -> tuple[str, str]:
    """Retrieve username and password from Kubernetes Secret.
    
    Args:
        secret_name: Name of the secret
        secret_namespace: Namespace of the secret
        
    Returns:
        tuple: (username, password)
        
    Raises:
        ValueError: If secret not found or missing required keys
    """
    try:
        secrets = list(kr8s.get("secrets", secret_name, namespace=secret_namespace))
        if not secrets:
            raise ValueError(f"Secret {secret_name} not found in namespace {secret_namespace}")
        
        secret = secrets[0]
        username_b64 = secret.data.get('username')
        password_b64 = secret.data.get('password')
        
        if not username_b64:
            raise ValueError(f"Secret {secret_name} does not contain 'username' key")
        if not password_b64:
            raise ValueError(f"Secret {secret_name} does not contain 'password' key")
        
        username = base64.b64decode(username_b64).decode('utf-8')
        password = base64.b64decode(password_b64).decode('utf-8')
        return username, password
    except Exception as e:
        logger.error(f"Failed to retrieve credentials from secret {secret_namespace}/{secret_name}: {e}")
        raise


def register_handlers(inj: Injector):
    global injector, api
    injector = inj
    api = inj.get(ApiClient)
    logger.info("Registering UptimeKumaMonitor handlers...")
    UptimeKumaMonitor.install(api, exist_ok=True)


@kopf.on.update("ops.veitosiander.de", "v1", "UptimeKumaMonitor")
def update_monitor(spec, name, namespace, **kwargs):
    monitor_management = injector.get(MonitorManagement)
    logger.info(f"Updating UptimeKumaMonitor resource: {namespace}/{name}")

    monitor_id = spec.get('monitor_id')
    if not monitor_id:
        logger.warning(f"No monitor_id for {namespace}/{name}, skipping update.")
        return

    kuma_api = None
    try:
        username, password = get_credentials_from_secret(
            spec['existing_secret'],
            namespace
        )

        kuma_api = monitor_management.connect_to_kuma(
            spec['kuma_url'],
            username,
            password
        )

        existing_monitor = monitor_management.get_monitor_by_id(kuma_api, monitor_id)
        if not existing_monitor:
            logger.warning(f"Monitor with id '{monitor_id}' not found. Skipping update.")
            return

        monitor_config = monitor_management.build_monitor_config(spec)
        monitor_management.update_monitor(kuma_api, monitor_id, monitor_config)
        logger.info(f"Successfully updated monitor with ID {monitor_id}")

    except Exception as e:
        logger.error(f"Failed to update monitor for {namespace}/{name}: {e}")
        raise
    finally:
        if kuma_api:
            monitor_management.disconnect_api(kuma_api)

@kopf.on.create("ops.veitosiander.de", "v1", "UptimeKumaMonitor")
def create_monitor(spec, name, namespace, **kwargs):
    monitor_management = injector.get(MonitorManagement)
    logger.info(f"Creating UptimeKumaMonitor resource: {namespace}/{name}")

    kuma_api = None
    try:
        username, password = get_credentials_from_secret(
            spec['existing_secret'],
            namespace
        )

        kuma_api = monitor_management.connect_to_kuma(
            spec['kuma_url'],
            username,
            password
        )

        existing_monitor = monitor_management.get_monitor_by_name(kuma_api, spec['name'])
        if existing_monitor:
            logger.info(f"Monitor with name '{spec['name']}' already exists. Skipping creation.")
            monitor_id = existing_monitor['id']
            cr = list(kr8s.get("UptimeKumaMonitor.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({"spec": {"monitor_id": monitor_id, "is_installed": True}})
            logger.info(f"UptimeKumaMonitor {namespace}/{name} status updated with existing monitor_id: {monitor_id}")
            return {'monitor_id': monitor_id}

        monitor_config = monitor_management.build_monitor_config(spec)
        created_monitor = monitor_management.create_monitor(kuma_api, monitor_config)

        monitor_id = created_monitor.get('monitorID')
        if monitor_id:
            logger.info(f"Successfully created monitor with ID {monitor_id}")
            # Update the CR with the new monitor_id
            cr = list(kr8s.get("UptimeKumaMonitor.ops.veitosiander.de", name, namespace=namespace))[0]
            cr.patch({"spec": {"monitor_id": monitor_id, "is_installed": True}})
            logger.info(f"UptimeKumaMonitor {namespace}/{name} status updated with monitor_id: {monitor_id}")
        else:
            logger.error("Failed to get monitorID from creation result.")

    except Exception as e:
        logger.error(f"Failed to create monitor for {namespace}/{name}: {e}")
        raise
    finally:
        if kuma_api:
            monitor_management.disconnect_api(kuma_api)

@kopf.on.delete("ops.veitosiander.de", "v1", "UptimeKumaMonitor")
def delete_monitor(spec, name, namespace, **kwargs):
    monitor_management = injector.get(MonitorManagement)
    
    logger.info(f"Deleting UptimeKumaMonitor resource: {namespace}/{name}")
    
    monitor_id = spec.get('monitor_id', 0)
    if monitor_id == 0:
        logger.info(f"No monitor_id for {namespace}/{name}, nothing to delete from Uptime Kuma.")
        return
    
    kuma_api = None
    try:
        # Retrieve credentials from secret in the same namespace as the CR
        username, password = get_credentials_from_secret(
            spec['existing_secret'],
            namespace
        )
        
        # Connect to Uptime Kuma
        kuma_api = monitor_management.connect_to_kuma(
            spec['kuma_url'],
            username,
            password
        )
        
        # Delete monitor
        monitor_management.delete_monitor(kuma_api, monitor_id)
        logger.info(f"UptimeKumaMonitor {namespace}/{name} deleted successfully from Uptime Kuma.")
        
    except Exception as e:
        logger.error(f"Failed to delete monitor {monitor_id} for {namespace}/{name}: {e}")
        # Don't raise exception on delete to allow cleanup to proceed
        pass
    finally:
        if kuma_api:
            monitor_management.disconnect_api(kuma_api)
