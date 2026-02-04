# Secret AI LLM Client
"""
Wrapper for Secret AI using OpenAI-compatible endpoint.
Based on https://github.com/MrGarbonzo/secretGPT
"""

import structlog
from typing import Optional, Generator, AsyncGenerator
from pydantic import BaseModel

from .config import settings

log = structlog.get_logger()


def _get_secret_ai_base_url() -> str:
    """Get Secret AI OpenAI-compatible endpoint URL."""
    base = settings.secret_ai_base_url.rstrip("/")
    # Ensure /v1 suffix for OpenAI compatibility
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


# Available models from Secret AI
SECRET_AI_MODELS = [
    "deepseek-r1:70b",
    "gemma3:4b",
    "llama3.2-vision:latest",
    "llama3.3:70b",
    "qwen3:8b",
]


class Message(BaseModel):
    """A chat message."""
    role: str  # "system", "human", "assistant"
    content: str


class LLMResponse(BaseModel):
    """Response from the LLM."""
    content: str
    model: str
    usage: Optional[dict] = None


class SecretAIClient:
    """
    Client for Secret AI confidential LLM inference.

    Uses OpenAI-compatible endpoint at Secret Network.

    Usage:
        client = SecretAIClient()
        response = client.invoke([
            Message(role="system", content="You are helpful."),
            Message(role="human", content="Hello!")
        ])
        print(response.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        self.api_key = api_key or settings.secret_ai_api_key
        self.model_name = model or settings.secret_ai_model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = None
        self._async_client = None
        self._model = None
        self._base_url = None
        self._initialized = False

    def _initialize(self):
        """Initialize the OpenAI client for Secret AI endpoint."""
        if self._initialized:
            return

        if not self.api_key:
            log.warning("No Secret AI API key provided, LLM will not be available")
            self._initialized = True
            return

        try:
            from openai import OpenAI, AsyncOpenAI

            log.info("Initializing Secret AI client", model=self.model_name)

            # Find matching model
            self._model = None
            for m in SECRET_AI_MODELS:
                if self.model_name.lower() in m.lower():
                    self._model = m
                    break

            if not self._model:
                # Default to deepseek-r1:70b
                self._model = "deepseek-r1:70b"
                log.warning(f"Model {self.model_name} not found, using {self._model}")

            # Secret AI expects API key in X-API-Key header
            default_headers = {
                "X-API-Key": self.api_key
            }

            base_url = _get_secret_ai_base_url()

            self._client = OpenAI(
                base_url=base_url,
                api_key=self.api_key,
                default_headers=default_headers
            )

            self._async_client = AsyncOpenAI(
                base_url=base_url,
                api_key=self.api_key,
                default_headers=default_headers
            )

            self._initialized = True
            self._base_url = base_url
            log.info("Secret AI client initialized successfully",
                     model=self._model,
                     base_url=base_url)

        except ImportError:
            log.error("openai package not installed. Install with: pip install openai")
            self._initialized = True
        except Exception as e:
            log.error("Failed to initialize Secret AI client", error=str(e))
            self._initialized = True

    def _ensure_initialized(self):
        """Ensure client is initialized."""
        if not self._initialized:
            self._initialize()

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert messages to OpenAI format."""
        openai_messages = []
        for msg in messages:
            role = msg.role
            if role == "human":
                role = "user"
            openai_messages.append({
                "role": role,
                "content": msg.content
            })
        return openai_messages

    def invoke(self, messages: list[Message]) -> LLMResponse:
        """
        Send messages and get a response.

        Args:
            messages: List of chat messages

        Returns:
            LLMResponse with content
        """
        self._ensure_initialized()

        if self._client is None:
            log.warning("LLM client not available, returning empty response")
            return LLMResponse(
                content="[]",
                model=self.model_name,
            )

        openai_messages = self._convert_messages(messages)
        log.debug("Invoking Secret AI", num_messages=len(messages), model=self._model)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content
            log.debug("Secret AI response received", length=len(content))

            return LLMResponse(
                content=content,
                model=self._model,
            )
        except Exception as e:
            log.error("Secret AI invocation failed", error=str(e))
            raise

    def stream(self, messages: list[Message]) -> Generator[str, None, None]:
        """
        Stream response tokens.

        Args:
            messages: List of chat messages

        Yields:
            Response tokens as they arrive
        """
        self._ensure_initialized()

        if self._client is None:
            log.warning("LLM client not available, returning empty stream")
            yield "[]"
            return

        openai_messages = self._convert_messages(messages)
        log.debug("Streaming from Secret AI", num_messages=len(messages))

        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content

        except Exception as e:
            log.error("Secret AI streaming failed", error=str(e))
            raise

    @property
    def model(self) -> str:
        """Get the model name."""
        return self._model or self.model_name

    @property
    def base_url(self) -> str:
        """Get the Secret AI base URL."""
        return self._base_url or _get_secret_ai_base_url()


# ============ Convenience Functions ============

def create_message(role: str, content: str) -> Message:
    """Create a chat message."""
    return Message(role=role, content=content)


def system(content: str) -> Message:
    """Create a system message."""
    return create_message("system", content)


def human(content: str) -> Message:
    """Create a human message."""
    return create_message("human", content)


def assistant(content: str) -> Message:
    """Create an assistant message."""
    return create_message("assistant", content)
