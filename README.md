# LLM Operator

A Kubernetes operator for managing LiteLLM, Ollama, etc. resources, providing seamless integration of AI models from multiple providers through Custom Resource Definitions.

This operator extends Kubernetes with custom resources to manage LiteLLM keys and models, enabling declarative configuration of AI model endpoints from various providers including OpenAI, Anthropic, and Ollama.

## Installation

```bash
helm install llm-operator oci://ghcr.io/vosiander/llm-operator
```

## Usage

### Managing API Keys

Create a LiteLLM API key resource:

```yaml
apiVersion: ops.veitosiander.de/v1
kind: LiteLLMKey
metadata:
  name: example-key
  namespace: default
spec:
  litellm_host: "https://litellm.example.com"
  litellm_api_key: "your-master-key-here"
  key_name: "user-api-key"
  key_alias: "main-api-key"
  user_id: "user-123"
```

### Configuring AI Models

#### OpenAI GPT-4

```yaml
apiVersion: ops.veitosiander.de/v1
kind: LiteLLMModel
metadata:
  name: openai-gpt4
  namespace: default
spec:
  litellm_host: "https://litellm.example.com"
  litellm_api_key: "your-master-key-here"
  model_name: "gpt4-openai"
  litellm_params:
    model: "openai/gpt-4"
    api_key: "sk-your-openai-api-key-here"
  model_info: {}
```

#### Anthropic Claude

```yaml
apiVersion: ops.veitosiander.de/v1
kind: LiteLLMModel
metadata:
  name: anthropic-claude
  namespace: default
spec:
  litellm_host: "https://litellm.example.com"
  litellm_api_key: "your-master-key-here"
  model_name: "claude-anthropic"
  litellm_params:
    model: "anthropic/claude-3-sonnet-20240229"
    api_key: "sk-ant-your-anthropic-key-here"
  model_info: {}
```

#### Ollama Models

Self-hosted Ollama models:

```yaml
apiVersion: ops.veitosiander.de/v1
kind: LiteLLMModel
metadata:
  name: ollama-gemma3
  namespace: default
spec:
  litellm_host: "https://litellm.example.com"
  litellm_api_key: "your-master-key-here"
  model_name: "gemma3-ollama"
  litellm_params:
    api_base: "http://ollama.example.com:11434"
    model: "ollama/gemma3"
  model_info: {}
```

### Manage Ollama Models

Manages ollama models via Ollama's HTTP API. Pulls the model if not already available. Deletes the model if CRD is deleted.

```yaml
apiVersion: ops.veitosiander.de/v1
kind: OllamaModel
metadata:
  name: ollama-magistral-small-2509-gguf
  namespace: default
spec:
  ollama_host: "http://127.0.0.1:11434"
  model: "hf.co/mistralai/Magistral-Small-2509-GGUF"
  tag: "Q8_0"
```

### Managing n8n Admin Users

Creates admin users in n8n instances for workflow automation platform management.

```yaml
apiVersion: ops.veitosiander.de/v1
kind: N8nAdminUser
metadata:
  name: n8n-admin-user-example
  namespace: default
spec:
  n8n_domain: "https://n8n.example.com"
  email: "admin@example.com"
  password: "SecurePassword123!"
  first_name: "Admin"
  last_name: "User"
```

### Managing n8n API Keys

Creates API keys for n8n workflow automation and stores them as Kubernetes secrets.

```yaml
apiVersion: ops.veitosiander.de/v1
kind: N8nApiKey
metadata:
  name: n8n-api-key-example
  namespace: default
spec:
  n8n_domain: "https://n8n.example.com"
  email: "admin@example.com"
  password: "SecurePassword123!"
  api_key_name: "workflow-automation-key"
  secret_name: "n8n-api-secret"
  secret_namespace: "default"
```

## Configuration

### LiteLLMKey Spec

- `litellm_host`: LiteLLM server endpoint
- `litellm_api_key`: Master API key for LiteLLM server
- `key_name`: Name for the generated key
- `key_alias`: Human-readable alias for the key
- `user_id`: Associated user identifier

### LiteLLMModel Spec

- `litellm_host`: LiteLLM server endpoint
- `litellm_api_key`: Master API key for LiteLLM server
- `model_name`: Internal model identifier
- `litellm_params`: Provider-specific model configuration
- `model_info`: Additional model metadata

### OllamaModel Spec

- `ollama_host`: Ollama server endpoint
- `model`: Model identifier (e.g., huggingface repository)
- `tag`: Model tag/variant to pull

### N8nAdminUser Spec

- `n8n_domain`: n8n instance URL
- `email`: Admin user email address
- `password`: Admin user password
- `first_name`: Admin user first name
- `last_name`: Admin user last name

### N8nApiKey Spec

- `n8n_domain`: n8n instance URL
- `email`: User email for authentication
- `password`: User password for authentication
- `api_key_name`: Name for the generated API key
- `secret_name`: Kubernetes secret name to store the API key
- `secret_namespace`: Kubernetes namespace for the secret

## Development

### Requirements

- Python 3.13+
- uv package manager

### Setup

```bash
# Install dependencies
uv sync

# Run the operator locally
uv run kopf run main.py
```

## License

This project is licensed under the terms specified in the LICENSE file.
