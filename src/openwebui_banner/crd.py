import kubecrd
from dataclasses import dataclass, field

@dataclass
class OpenWebUIBanner(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    openwebui_api_key: str
    openwebui_host: str
    id: str
    type: str
    content: str
    dismissible: bool = field(default=True)
    timestamp: int = field(default=0)
    title: str = field(default="")

    is_installed: bool = field(default=False, metadata={"description": "Indicates if the banner is installed."})
