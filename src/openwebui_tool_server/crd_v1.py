import kubecrd
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class OpenWebUIToolServerAccessControlRead(kubecrd.KubeResourceBase):
    group_ids: List[str] = field(default_factory=list)
    user_ids: List[str] = field(default_factory=list)


@dataclass
class OpenWebUIToolServerAccessControlWrite(kubecrd.KubeResourceBase):
    group_ids: List[str] = field(default_factory=list)
    user_ids: List[str] = field(default_factory=list)


@dataclass
class OpenWebUIToolServerAccessControl(kubecrd.KubeResourceBase):
    read: OpenWebUIToolServerAccessControlRead = field(default=None)
    write: OpenWebUIToolServerAccessControlWrite = field(default=None)


@dataclass
class OpenWebUIToolServerConfig(kubecrd.KubeResourceBase):
    access_control: OpenWebUIToolServerAccessControl = field(default=None)
    enable: bool = field(default=True)


@dataclass
class OpenWebUIToolServerInfo(kubecrd.KubeResourceBase):
    name: str
    description: str = field(default="")
    id: str = field(default="")


@dataclass
class OpenWebUIToolServerV1(kubecrd.KubeResourceBase):
    __group__ = "ops.veitosiander.de"
    __version__ = "v1"

    openwebui_host: str

    # Tool server configuration matching API format
    url: str
    path: str
    openwebui_api_key: str = field(default="", metadata={"description": "DEPRECATED: API key for authentication. Please migrate to v2 using existing_secret field"})
    
    # Optional fields with defaults
    type: str = field(default="openapi")
    auth_type: str = field(default="bearer")
    key: str = field(default="")
    spec: str = field(default="")
    spec_type: str = field(default="url")
    info: OpenWebUIToolServerInfo = field(default=None)
    config: OpenWebUIToolServerConfig = field(default=None)
    is_installed: bool = field(default=False, metadata={"description": "Indicates if the tool server is installed."})
