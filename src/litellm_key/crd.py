import kubecrd
from dataclasses import dataclass, field

@dataclass
class LiteLLMKey(kubecrd.KubeResourceBase):
    __group__ = 'ops.veitosiander.de'
    __version__ = 'v1'

    litellm_host: str
    litellm_api_key: str

    key_name: str
    key_alias: str
    user_id: str
    key_value: str = field(default="", metadata={"description": "The actual API key value."})
