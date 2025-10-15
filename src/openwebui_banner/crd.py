import kubecrd
from dataclasses import dataclass, field

@dataclass
class OpenWebUIBanner(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    # Required fields
    openwebui_host: str
    id: str
    type: str
    content: str
    
    # Optional fields with defaults
    dismissible: bool = field(default=True)
    timestamp: int = field(default=0)
    title: str = field(default="")
    openwebui_api_key: str = field(default="", metadata={"description": "Optional: API key for authentication. If not provided, the operator will attempt to use other authentication methods"})
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the banner is installed."})
