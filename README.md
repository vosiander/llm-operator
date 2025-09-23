# LLM Operator

A Kubernetes operator for managing LiteLLM, Ollama, etc. resources, providing seamless integration of AI models from multiple providers through Custom Resource Definitions.

## Overview

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
