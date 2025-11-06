from injector import singleton
from loguru import logger
from uptime_kuma_api import UptimeKumaApi


class UptimeKumaSetupException(Exception):
    """Raised for setup/connection errors"""
    pass


@singleton
class SetupManagement:
    def __init__(self):
        pass

    def setup(self, kuma_url: str, username: str, password: str) -> bool:
        """
        Setup Uptime Kuma.
        
        Args:
            kuma_url: Uptime Kuma instance URL
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            logger.info(f"Connecting to Uptime Kuma at {kuma_url}")
            api = UptimeKumaApi(kuma_url)
            api.setup(username, password)
            logger.info(f"Successfully connected to {kuma_url}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            if 'api' in locals():
                api.disconnect()
            return False

    def need_setup(self, kuma_url: str) -> bool:
        """
        Check if already setup.

        Args:
            kuma_url: Uptime Kuma instance URL

        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            logger.info(f"Connecting to Uptime Kuma at {kuma_url}")
            api = UptimeKumaApi(kuma_url)
            return api.need_setup()
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            if 'api' in locals():
                api.disconnect()
            return True
