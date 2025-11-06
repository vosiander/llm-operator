from injector import singleton
from loguru import logger
from uptime_kuma_api import UptimeKumaApi


class UptimeKumaMonitorException(Exception):
    """Raised for monitor operation errors"""
    pass


class MonitorType:
    """Monitor type constants"""
    HTTP = "http"
    TCP = "port"
    PING = "ping"


@singleton
class MonitorManagement:
    def __init__(self):
        pass

    def connect_to_kuma(self, kuma_url: str, username: str, password: str):
        """Create authenticated API client.
        
        Args:
            kuma_url: Uptime Kuma instance URL
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            UptimeKumaApi: Authenticated API client
            
        Raises:
            UptimeKumaMonitorException: If connection fails
        """
        try:
            logger.info(f"Connecting to Uptime Kuma at {kuma_url}")
            api = UptimeKumaApi(kuma_url)
            api.login(username, password)
            logger.info(f"Successfully connected to {kuma_url}")
            return api
        except Exception as e:
            logger.error(f"Failed to connect to Uptime Kuma at {kuma_url}: {e}")
            raise UptimeKumaMonitorException(f"Failed to connect: {e}")

    def get_monitor_by_id(self, api, monitor_id: int):
        """Fetch monitor details.
        
        Args:
            api: UptimeKumaApi instance
            monitor_id: Monitor ID to fetch
            
        Returns:
            dict: Monitor details or None if not found
        """
        try:
            monitors = api.get_monitors()
            for monitor in monitors:
                if monitor.get('id') == monitor_id:
                    return monitor
            logger.warning(f"Monitor with ID {monitor_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get monitor {monitor_id}: {e}")
            return None

    def create_monitor(self, api, monitor_data: dict):
        """Create new monitor.
        
        Args:
            api: UptimeKumaApi instance
            monitor_data: Monitor configuration
            
        Returns:
            dict: Created monitor with monitorID
            
        Raises:
            UptimeKumaMonitorException: If creation fails
        """
        try:
            logger.info(f"Creating monitor: {monitor_data.get('name')}")
            result = api.add_monitor(**monitor_data)
            logger.info(f"Successfully created monitor with ID {result.get('monitorID')}")
            return result
        except Exception as e:
            logger.error(f"Failed to create monitor: {e}")
            raise UptimeKumaMonitorException(f"Failed to create monitor: {e}")

    def update_monitor(self, api, monitor_id: int, monitor_data: dict):
        """Modify existing monitor.
        
        Args:
            api: UptimeKumaApi instance
            monitor_id: Monitor ID to update
            monitor_data: New monitor configuration
            
        Returns:
            dict: Updated monitor result
            
        Raises:
            UptimeKumaMonitorException: If update fails
        """
        try:
            logger.info(f"Updating monitor {monitor_id}")
            # Pass monitor_id as first positional argument (id_)
            result = api.edit_monitor(monitor_id, **monitor_data)
            logger.info(f"Successfully updated monitor {monitor_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update monitor {monitor_id}: {e}")
            raise UptimeKumaMonitorException(f"Failed to update monitor: {e}")

    def delete_monitor(self, api, monitor_id: int) -> bool:
        """Remove monitor from Uptime Kuma.
        
        Args:
            api: UptimeKumaApi instance
            monitor_id: Monitor ID to delete
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            UptimeKumaMonitorException: If deletion fails
        """
        try:
            logger.info(f"Deleting monitor {monitor_id}")
            api.delete_monitor(monitor_id)
            logger.info(f"Successfully deleted monitor {monitor_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete monitor {monitor_id}: {e}")
            raise UptimeKumaMonitorException(f"Failed to delete monitor: {e}")

    def upsert_monitor(self, api, monitor_id: int, monitor_data: dict):
        """Idempotent create/update.
        
        Args:
            api: UptimeKumaApi instance
            monitor_id: Monitor ID (0 for new monitor)
            monitor_data: Monitor configuration
            
        Returns:
            dict: Monitor result with monitorID
            
        Raises:
            UptimeKumaMonitorException: If operation fails
        """
        if monitor_id > 0:
            # Check if monitor exists
            existing = self.get_monitor_by_id(api, monitor_id)
            if existing:
                logger.info(f"Monitor {monitor_id} exists, updating...")
                return self.update_monitor(api, monitor_id, monitor_data)
            else:
                logger.warning(f"Monitor {monitor_id} not found, creating new monitor...")
        
        # Create new monitor
        logger.info("Creating new monitor...")
        return self.create_monitor(api, monitor_data)

    def validate_monitor_type(self, monitor_type: str) -> bool:
        """Check if type is http/tcp/ping.
        
        Args:
            monitor_type: Monitor type to validate
            
        Returns:
            bool: True if valid type
        """
        valid_types = [MonitorType.HTTP, MonitorType.TCP, MonitorType.PING]
        return monitor_type in valid_types

    def build_monitor_config(self, spec: dict):
        """Transform CRD spec to API format.
        
        Args:
            spec: CRD spec dictionary
            
        Returns:
            dict: Monitor configuration for Uptime Kuma API
            
        Raises:
            UptimeKumaMonitorException: If validation fails
        """
        monitor_type = spec.get('type', 'http')
        
        # Validate monitor type
        if not self.validate_monitor_type(monitor_type):
            raise UptimeKumaMonitorException(f"Invalid monitor type: {monitor_type}")
        
        # Base configuration
        config = {
            'type': monitor_type,
            'name': spec.get('name'),
            'interval': spec.get('interval', 60),
            'retryInterval': spec.get('retry_interval', 60),
        }
        
        # Type-specific configuration
        if monitor_type == MonitorType.HTTP:
            if not spec.get('url'):
                raise UptimeKumaMonitorException("URL is required for HTTP monitors")
            config['url'] = spec['url']
        elif monitor_type == MonitorType.TCP:
            if not spec.get('hostname'):
                raise UptimeKumaMonitorException("Hostname is required for TCP monitors")
            config['hostname'] = spec['hostname']
            config['port'] = spec.get('port', 80)
        elif monitor_type == MonitorType.PING:
            if not spec.get('hostname'):
                raise UptimeKumaMonitorException("Hostname is required for PING monitors")
            config['hostname'] = spec['hostname']
        
        logger.debug(f"Built monitor config: {config}")
        return config

    def disconnect_api(self, api) -> None:
        """Clean up API connection.
        
        Args:
            api: UptimeKumaApi instance to disconnect
        """
        try:
            if api:
                api.disconnect()
                logger.debug("Disconnected from Uptime Kuma API")
        except Exception as e:
            logger.warning(f"Error disconnecting from API: {e}")
