# SecretVM & Secret AI Reference

## SecretVM Overview

SecretVM is Secret Network's Confidential Virtual Machine framework, allowing developers to deploy secure workloads within Trusted Execution Environments (TEEs).

### Key Features

- **Data Confidentiality**: TEEs ensure even hardware owners can't access data inside the VM
- **Remote Attestation**: Cryptographic verification that trusted code runs in secure enclave
- **Language/Stack Agnostic**: Supports Docker containers in any language/framework
- **Low Overhead**: 5-7% performance overhead even for LLM inference

### Supported Hardware

- Intel Trust Domain Extensions (TDX)
- AMD Secure Encrypted Virtualization (SEV)

### Use Cases

- Secure LLM inference and fine-tuning
- Autonomous AI agents
- Confidential multi-agent coordination (MCP servers)
- Encrypted trading algorithms
- Privacy-preserving data processing

## SecretVM Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SecretVM Instance                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Guest Container                        │  │
│  │              (Your Docker application)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Secret CVM Runtime                       │  │
│  │         (Handles attestation, key management)             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      Rootfs                               │  │
│  │    (Poky Linux + NVIDIA drivers + runtime components)     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      Kernel                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Initramfs                              │  │
│  │       (Performs measurements, extends chain of trust)     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Attestation Quote
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  On-Chain KMS Contract                          │
│         (Validates quote, returns encryption key)               │
└─────────────────────────────────────────────────────────────────┘
```

### Components

- **Initramfs**: Temporary root filesystem that performs measurements
- **Kernel**: Linux kernel for the VM
- **Rootfs**: Poky Linux OS with drivers and runtime
- **Guest Container**: Your Docker application
- **docker-compose.yaml**: Describes container configuration

## Deploying to SecretVM

### Current Process (Manual)

1. Prepare docker-compose.yml with your application
2. Access SecretVM environment
3. Deploy docker-compose manually
4. Custom domains are created automatically

### Docker Compose Example

```yaml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_AI_API_KEY=${SECRET_AI_API_KEY}
      - MOLTBOOK_API_KEY=${MOLTBOOK_API_KEY}
    volumes:
      - agent-data:/data
    restart: unless-stopped

volumes:
  agent-data:
```

## Secret AI

### Overview

Secret AI provides confidential LLM inference via the Secret AI SDK. Queries are processed inside TEEs, ensuring privacy.

### Available Models

- DeepSeek-R1-70B (primary model we're using)
- Other models available via SDK

### SDK Installation

```bash
pip install secret-ai-sdk
```

### Basic Usage

```python
from secret_ai_sdk import ChatSecret, Secret

# Initialize
secret = Secret()
models = secret.get_models()
urls = secret.get_urls(model=models[0])

# Create client
client = ChatSecret(
    base_url=urls[0],
    model=models[0],
    temperature=0.7,
    max_tokens=2000
)

# Simple invoke
response = client.invoke([
    ("system", "You are a helpful assistant."),
    ("human", "What is confidential computing?")
])
print(response.content)

# Streaming
for chunk in client.stream([("human", "Explain TEEs")]):
    print(chunk.content, end="", flush=True)
```

### Conversation History

```python
conversation_history = [
    ("system", "You are a privacy expert."),
]

def chat(user_message):
    conversation_history.append(("human", user_message))
    response = client.invoke(conversation_history)
    conversation_history.append(("assistant", response.content))
    return response.content
```

### Environment Variables

```bash
export SECRET_AI_API_KEY=your_api_key_here
```

### Performance Optimization

```python
# Optimize for speed
fast_client = ChatSecret(
    base_url=url,
    model=model,
    max_tokens=500,        # Limit response length
    temperature=0.3,       # Lower = faster
    client_kwargs={
        'timeout': 45.0,   # Increase timeout
        'max_retries': 2   # Reduce retries
    }
)
```

## Secret Network SDK (Python)

For blockchain interactions (future wallet integration):

```bash
pip install secret-sdk
```

### Basic Usage

```python
from secret_sdk.client.lcd import LCDClient
from secret_sdk.key.mnemonic import MnemonicKey

# Connect to network
secret = LCDClient(
    url="https://lcd.secret.express",
    chain_id="secret-4"
)

# Create wallet
mk = MnemonicKey(mnemonic="your mnemonic here")
wallet = secret.wallet(mk)

# Query balance
balance = secret.bank.balance(wallet.key.acc_address)
```

## References

- [SecretVM Docs](https://docs.scrt.network/secret-network-documentation/secretvm-confidential-virtual-machines/introduction)
- [Secret AI SDK](https://github.com/scrtlabs/secret-ai-sdk)
- [Secret SDK Python](https://github.com/secretanalytics/secret-sdk-python)
- [Secret Network Docs](https://docs.scrt.network)
