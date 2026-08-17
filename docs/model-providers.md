# Model Providers

HackerGPT Local uses backend provider adapters. The browser never calls model runtimes directly.

## Ollama

Ollama is enabled by default in `config/models.yaml` at `http://127.0.0.1:11434`. The adapter uses Ollama's local HTTP API for health, installed model discovery, running model state, and non-streaming test generation.

Useful manual checks:

```powershell
ollama --version
ollama list
ollama ps
Invoke-WebRequest http://127.0.0.1:11434/api/version
```

No model is downloaded automatically. If no model is installed, the Models page renders an empty state.

## llama.cpp

The `llama_cpp` provider is disabled by default and expects a running `llama-server`-style OpenAI-compatible endpoint, configured with `HACKERGPT_LLAMA_CPP_BASE_URL` or `config/models.yaml`.

The adapter reports unavailable metadata as unknown rather than fabricating quantization or context values.

## OpenAI-Compatible

The `openai_compatible` provider supports local or explicitly configured compatible endpoints such as LM Studio, LocalAI, or other servers. API keys are backend-only and are never returned through frontend APIs.

External non-loopback endpoints are blocked unless central policy allows network access.

## vLLM

The `vllm` provider is configured as an OpenAI-compatible endpoint adapter. vLLM is not installed or required on this Windows machine. It may point to a server running under Linux, WSL, another local machine, or a remote environment when policy explicitly allows it.

## Configuration

Primary config lives in `config/models.yaml`. Environment overrides include:

- `HACKERGPT_OLLAMA_ENABLED`
- `HACKERGPT_OLLAMA_BASE_URL`
- `HACKERGPT_LLAMA_CPP_ENABLED`
- `HACKERGPT_LLAMA_CPP_BASE_URL`
- `HACKERGPT_OPENAI_COMPATIBLE_ENABLED`
- `HACKERGPT_OPENAI_COMPATIBLE_BASE_URL`
- `HACKERGPT_OPENAI_COMPATIBLE_API_KEY`
- `HACKERGPT_VLLM_ENABLED`
- `HACKERGPT_VLLM_BASE_URL`
- `HACKERGPT_VLLM_API_KEY`

Cloud fallback is not implemented and must never happen silently.
