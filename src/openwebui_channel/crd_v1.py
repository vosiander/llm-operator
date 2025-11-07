import kubecrd
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class OpenWebUIChannelData(kubecrd.KubeResourceBase):
    max_members: int = field(default=0)
    allow_guests: bool = field(default=False)

@dataclass
class OpenWebUIChannelMeta(kubecrd.KubeResourceBase):
    category: str = field(default_factory=lambda: "general")
    priority: str = field(default_factory=lambda: "normal")

@dataclass
class OpenWebUIChannelAccessControl(kubecrd.KubeResourceBase):
    read: list[str] = field(default_factory=lambda: ["admin", "user"])
    write: list[str] = field(default_factory=lambda: ["admin", "user"])

@dataclass
class OpenWebUIChannelV1(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    openwebui_host: str

    # Channel configuration
    name: str
    openwebui_api_key: str = field(default="", metadata={"description": "DEPRECATED: API key for authentication. Please migrate to v2 using existing_secret field"})
    
    # Optional fields with defaults
    description: str = field(default="")
    type: str = field(default=None)
    data: OpenWebUIChannelData = field(default=None)
    meta: OpenWebUIChannelMeta = field(default=None)
    access_control: OpenWebUIChannelAccessControl = field(default=None)
    channel_id: str = field(default="")
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the channel is installed."})
