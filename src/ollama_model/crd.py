import kubecrd
from dataclasses import dataclass, field

@dataclass
class OllamaModel(kubecrd.KubeResourceBase):
    __group__ = 'ops.veitosiander.de'
    __version__ = 'v1'

    ollama_host: str

    model: str = field(default="")
    tag: str = field(default="latest")

    api_key: str = field(default="", metadata={"description": "The API key for authenticating with the Ollama service."})
