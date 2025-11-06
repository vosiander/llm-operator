from injector import Injector
from kubernetes.client import ApiClient
from loguru import logger
import kopf
import kr8s
import base64

from src.uptime_kuma_setup.manager import SetupManagement
from src.uptime_kuma_setup.crd import UptimeKumaSetup

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
    logger.info("Registering UptimeKumaSetup handlers...")
    UptimeKumaSetup.install(api, exist_ok=True)


@kopf.on.create("ops.veitosiander.de", "v1", "UptimeKumaSetup")
@kopf.on.update("ops.veitosiander.de", "v1", "UptimeKumaSetup")
def test_setup(spec, name, namespace, **kwargs):
    setup_management = injector.get(SetupManagement)
    
    logger.info(f"Testing UptimeKumaSetup connection: {namespace}/{name}")
    
    try:
        # Retrieve credentials from secret in the same namespace as the CR
        username, password = get_credentials_from_secret(
            spec['existing_secret'],
            namespace
        )

        if not setup_management.need_setup(spec['kuma_url']):
            logger.info(f"UptimeKumaSetup {namespace}/{name} already set up.")
            return {"status": "already_setup"}
        
        if setup_management.setup(spec['kuma_url'], username, password):
            logger.info(f"UptimeKumaSetup {namespace}/{name} setup successful.")
            return {"status": "setup"}
        else:
            logger.warning(f"UptimeKumaSetup {namespace}/{name} setup failed.")
            raise kopf.TemporaryError("Connection test failed", delay=30)
            
    except ValueError as e:
        logger.error(f"Failed to retrieve credentials for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to retrieve credentials: {e}", delay=30)
    except Exception as e:
        logger.error(f"Failed to test connection for {namespace}/{name}: {e}")
        raise kopf.TemporaryError(f"Failed to test connection: {e}", delay=30)


@kopf.on.delete("ops.veitosiander.de", "v1", "UptimeKumaSetup")
def delete_setup(spec, name, namespace, **kwargs):
    logger.info(f"UptimeKumaSetup {namespace}/{name} deleted successfully.")
