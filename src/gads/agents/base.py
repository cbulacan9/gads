"""
Base Agent Class for GADS

Defines the abstract interface and shared functionality for all agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    
    name: str
    provider: ModelProvider
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt_path: str | None = None
    
    # Provider-specific settings
    api_key: str | None = None  # For Anthropic
    base_url: str | None = None  # For Ollama


class TokenUsage(BaseModel):
    """Token usage statistics from an LLM call."""
    
    input_tokens: int = 0
    output_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    def estimate_cost(self, model: str) -> float:
        """Estimate cost in USD based on model pricing."""
        # Pricing per million tokens (as of 2024)
        pricing = {
            # Anthropic
            "claude-opus-4-5-20250514": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
            # Older Claude models
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        }
        
        # Default to Opus pricing for unknown models
        rates = pricing.get(model, {"input": 15.0, "output": 75.0})
        
        cost = (self.input_tokens / 1_000_000 * rates["input"] +
                self.output_tokens / 1_000_000 * rates["output"])
        return cost


class AgentResponse(BaseModel):
    """Response from an agent."""
    
    content: str
    agent_name: str
    model: str
    
    # Structured outputs (optional)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    tokens_used: int | None = None  # Deprecated, use usage instead
    usage: TokenUsage | None = None  # Detailed token usage
    thinking: str | None = None  # For agents that show reasoning
    
    # Handoff information
    suggested_next_agent: str | None = None
    suggested_task: str | None = None


class BaseAgent(ABC):
    """
    Abstract base class for all GADS agents.
    
    Each agent specializes in a particular aspect of game development
    and can communicate with the orchestrator and other agents.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self._system_prompt: str | None = None
    
    @property
    def system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        if self._system_prompt is None:
            self._system_prompt = self._load_system_prompt()
        return self._system_prompt
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from file or return default."""
        if self.config.system_prompt_path:
            try:
                with open(self.config.system_prompt_path) as f:
                    return f.read()
            except FileNotFoundError:
                pass
        return self._default_system_prompt()
    
    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Return the default system prompt for this agent type."""
        ...
    
    @abstractmethod
    async def execute(
        self,
        user_input: str,
        context: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> AgentResponse:
        """
        Execute the agent's task.
        
        Args:
            user_input: The user's request or task description
            context: Current session context including project state
            history: Optional conversation history
            
        Returns:
            AgentResponse with the result
        """
        ...
    
    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, TokenUsage | None]:
        """
        Call the LLM with the given messages.
        
        This method handles provider-specific API calls.
        
        Returns:
            Tuple of (response_text, token_usage)
        """
        if self.config.provider == ModelProvider.ANTHROPIC:
            return await self._call_anthropic(messages, **kwargs)
        elif self.config.provider == ModelProvider.OLLAMA:
            return await self._call_ollama(messages, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
    
    async def _call_anthropic(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, TokenUsage]:
        """Call Anthropic's API."""
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=self.config.api_key)
        
        response = await client.messages.create(
            model=self.config.model,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=self.system_prompt,
            messages=messages,
        )
        
        # Extract token usage
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        
        return response.content[0].text, usage
    
    async def _call_ollama(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> tuple[str, TokenUsage | None]:
        """Call Ollama's API."""
        import aiohttp
        
        base_url = self.config.base_url or "http://localhost:11434"
        
        # Prepend system message
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": full_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self.config.temperature),
                    },
                },
            ) as response:
                data = await response.json()
                
                # Handle error responses from Ollama
                if "error" in data:
                    error_msg = data["error"]
                    if "not found" in error_msg.lower():
                        raise RuntimeError(
                            f"Ollama model '{self.config.model}' not found. "
                            f"Run: ollama pull {self.config.model}"
                        )
                    raise RuntimeError(f"Ollama error: {error_msg}")
                
                if response.status != 200:
                    raise RuntimeError(
                        f"Ollama API error: HTTP {response.status}"
                    )
                
                if "message" not in data:
                    raise RuntimeError(
                        f"Unexpected Ollama response format: {data}"
                    )
                
                # Ollama returns eval_count (output) and prompt_eval_count (input)
                usage = None
                if "eval_count" in data or "prompt_eval_count" in data:
                    usage = TokenUsage(
                        input_tokens=data.get("prompt_eval_count", 0),
                        output_tokens=data.get("eval_count", 0),
                    )
                
                return data["message"]["content"], usage
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, model={self.config.model!r})"
