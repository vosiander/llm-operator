import kubecrd
from dataclasses import dataclass, field


@dataclass
class UptimeKumaMonitor(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    # Connection
    kuma_url: str = field(metadata={"description": "Uptime Kuma instance URL"})
    existing_secret: str = field(metadata={"description": "Name of Kubernetes Secret with credentials"})
    
    # Monitor config
    name: str = field(metadata={"description": "Monitor display name"})
    type: str = field(default="http", metadata={"description": "Monitor type: http, tcp, or ping"})
    url: str = field(default="", metadata={"description": "URL for HTTP monitors"})
    hostname: str = field(default="", metadata={"description": "Hostname for TCP/PING monitors"})
    port: int = field(default=80, metadata={"description": "Port for TCP monitors"})
    interval: int = field(default=60, metadata={"description": "Check interval in seconds"})
    retry_interval: int = field(default=60, metadata={"description": "Retry interval in seconds"})
    
    # Status
    monitor_id: int = field(default=0, metadata={"description": "Uptime Kuma monitor ID"})
    is_installed: bool = field(default=False, metadata={"description": "Installation status"})
