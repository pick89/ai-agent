"""
AI Agent - Optimized Async Core Logic
Python 3.14 compatible, CPU-optimized, zero compiled dependencies
"""

import asyncio
import json
import re
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

import httpx

from config.settings import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    MAX_RESPONSE_TOKENS,
    CPU_THREADS,
    get_ollama_options
)
from config.advanced_settings import get_model_config


@dataclass
class ConversationContext:
    """Memory-efficient conversation management"""
    messages: List[Dict[str, str]] = field(default_factory=list)
    max_messages: int = 4
    estimated_tokens: int = 0

    def add(self, role: str, content: str):
        """Add message with smart pruning"""
        self.messages.append({"role": role, "content": content})
        # Rough token estimation (1 token ≈ 0.75 words)
        self.estimated_tokens += int(len(content.split()) * 1.3)

        # Prune old messages (keep system context, remove oldest pairs)
        while len(self.messages) > self.max_messages * 2:
            if len(self.messages) > 2:
                removed = self.messages.pop(1)  # Remove oldest user msg
                self.estimated_tokens -= int(len(removed["content"].split()) * 1.3)
                if len(self.messages) > 1:
                    removed = self.messages.pop(1)  # Remove corresponding assistant
                    self.estimated_tokens -= int(len(removed["content"].split()) * 1.3)

    def get_recent(self, n: int = 3) -> List[Dict[str, str]]:
        """Get recent context efficiently"""
        if len(self.messages) <= n:
            return self.messages.copy()
        # Always include first message (system), then last n-1
        return [self.messages[0]] + self.messages[-(n-1):] if self.messages else []

    def clear(self):
        """Reset context"""
        self.messages = []
        self.estimated_tokens = 0


class AsyncOllamaClient:
    """
    High-performance async Ollama client using httpx
    Connection pooling, keep-alive, timeout handling
    """

    def __init__(self, host: str = OLLAMA_HOST):
        self.host = host.rstrip('/')
        self._client: Optional[httpx.AsyncClient] = None
        self._timeout = httpx.Timeout(60.0, connect=10.0)

        # Connection pool limits
        limits = httpx.Limits(
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=30.0
        )

        self._limits = limits

    @property
    async def client(self) -> httpx.AsyncClient:
        """Lazy initialization with connection pooling"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=self._limits,
                http2=True,  # Enable HTTP/2 for multiplexing
            )
        return self._client

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict] = None,
        stream: bool = False
    ) -> str:
        """
        Send chat request to Ollama

        Args:
            model: Model name (e.g., "llama3.2:latest")
            messages: List of message dicts with role/content
            options: Generation options (temperature, etc.)
            stream: Whether to stream response (not implemented yet)

        Returns:
            Generated text response
        """
        client = await self.client

        url = f"{self.host}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,  # Non-streaming for simplicity
            "options": options or get_ollama_options(model),
        }

        start_time = time.time()

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            latency = time.time() - start_time

            # Log performance
            print(f"⏱️  Ollama: {latency:.2f}s | Model: {model}")

            return data["message"]["content"]

        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama request timed out after {self._timeout}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama HTTP error: {e.response.status_code} - {e.response.text[:200]}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {str(e)}")

    async def list_models(self) -> List[str]:
        """Get available models from Ollama"""
        client = await self.client
        url = f"{self.host}/api/tags"

        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            print(f"⚠️  Failed to list models: {e}")
            return []

    async def close(self):
        """Cleanup connections"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class OptimizedAgent:
    """
    High-performance async AI agent
    Features: connection pooling, context management, tool orchestration
    """

    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.context = ConversationContext(max_messages=4)
        self.client = AsyncOllamaClient()
        self.previous_searches: set = set()

        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "total_latency": 0.0,
            "errors": 0,
        }

        # Concurrency control
        self._semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

    def create_system_prompt(self, tools: Dict[str, Callable]) -> str:
        """Create efficient system prompt"""
        if not tools:
            return "You are a helpful AI assistant. Answer concisely and accurately."

        tools_desc = "\n".join([
            f"- {name}: {(func.__doc__ or 'No description').split(chr(10))[0][:80]}"
            for name, func in tools.items()
        ])

        return f"""You are an AI assistant with tool access.

Available tools:
{tools_desc}

CRITICAL RULES:
1. Use tools ONLY for current/real-time information
2. Tool call format: {{"tool": "name", "parameters": {{"key": "value"}}}}
3. Output ONLY the JSON when calling tools - no extra text
4. After tool results, provide a natural, concise answer

Be efficient and direct."""

    def parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract tool call from LLM response"""
        response = response.strip()

        # Fast path: pure JSON
        if response.startswith('{') and response.endswith('}'):
            try:
                data = json.loads(response)
                if isinstance(data, dict) and 'tool' in data:
                    return data
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        try:
            # Match nested braces carefully
            match = re.search(r'\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}', response)
            if match:
                data = json.loads(match.group())
                if isinstance(data, dict) and 'tool' in data:
                    return data
        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    async def execute_tool(
        self,
        tool_func: Callable,
        params: Dict[str, Any],
        timeout: int = 10
    ) -> tuple[str, str]:
        """
        Execute tool with timeout protection

        Returns:
            (status, result) tuple - status is 'success', 'timeout', or 'error'
        """
        try:
            if asyncio.iscoroutinefunction(tool_func):
                # Async function - use asyncio timeout
                result = await asyncio.wait_for(tool_func(**params), timeout=timeout)
            else:
                # Sync function - run in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool_func(**params)),
                    timeout=timeout
                )
            return 'success', str(result)

        except asyncio.TimeoutError:
            return 'timeout', f"Tool timed out after {timeout}s"
        except Exception as e:
            return 'error', str(e)[:200]

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None
    ) -> str:
        """Generate response with metrics tracking"""
        async with self._semaphore:  # Limit concurrency
            start = time.time()

            try:
                options = get_ollama_options(self.model)
                if temperature is not None:
                    options["temperature"] = temperature

                response = await self.client.chat(
                    model=self.model,
                    messages=messages,
                    options=options
                )

                latency = time.time() - start
                self.metrics["total_requests"] += 1
                self.metrics["total_latency"] += latency

                return response

            except Exception as e:
                self.metrics["errors"] += 1
                raise

    async def run(
        self,
        user_input: str,
        tools: Optional[Dict[str, Callable]] = None,
        max_iterations: int = 3
    ) -> str:
        """
        Main agent execution loop

        Args:
            user_input: User's message
            tools: Dictionary of available tools {name: function}
            max_iterations: Max tool use iterations

        Returns:
            Final response string
        """
        tools = tools or {}

        # Reset search tracking for new conversation
        if not self.context.messages:
            self.previous_searches.clear()

        # Add user message
        self.context.add("user", user_input)

        system_prompt = self.create_system_prompt(tools)

        for iteration in range(max_iterations):
            print(f"🔄 Iteration {iteration + 1}/{max_iterations}")

            # Build message list (system + recent context)
            recent_context = self.context.get_recent(3)
            messages = [{"role": "system", "content": system_prompt}] + recent_context

            try:
                # Generate response
                temp = 0.3 if iteration > 0 else 0.5  # Lower temp for follow-ups
                response = await self.generate_response(messages, temperature=temp)
                response = response.strip()

                # Log truncated response
                preview = response[:60] + "..." if len(response) > 60 else response
                print(f"🤖 Response: {preview}")

                # Check for tool call
                tool_call = self.parse_tool_call(response)

                if tool_call and tool_call.get('tool') in tools:
                    # Execute tool
                    tool_name = tool_call['tool']
                    params = tool_call.get('parameters', {})

                    # Deduplicate web searches
                    if tool_name == 'web_search':
                        query = params.get('query', '').lower().strip()
                        if query in self.previous_searches:
                            print(f"⚠️  Duplicate search skipped: {query}")
                            self.context.add("assistant", response)
                            self.context.add("user", "Already searched this. Answer with available info.")
                            continue
                        self.previous_searches.add(query)

                    print(f"🔧 Executing: {tool_name}")

                    # Execute with timeout
                    status, result = await self.execute_tool(tools[tool_name], params)

                    if status != 'success':
                        print(f"❌ Tool failed: {result}")
                        self.context.add("assistant", response)
                        self.context.add("user", f"Tool error: {result}")
                        continue

                    # Truncate long results
                    if len(result) > 2000:
                        result = result[:2000] + "... [truncated]"

                    # Add to context and continue
                    self.context.add("assistant", response)
                    self.context.add("user", f"Tool result: {result}")
                    continue

                elif tool_call:
                    # Tool not available
                    self.context.add("assistant", response)
                    self.context.add("user", f"Tool '{tool_call.get('tool')}' unavailable. Answer directly.")
                    continue

                else:
                    # Final response - no tool call
                    self.context.add("assistant", response)
                    return response

            except Exception as e:
                error_msg = f"Error: {str(e)[:100]}"
                print(f"❌ {error_msg}")
                return f"I encountered an error: {error_msg}"

        # Max iterations reached
        return "I've tried multiple approaches. Could you rephrase your question?"

    def reset_conversation(self):
        """Clear conversation history"""
        self.context.clear()
        self.previous_searches.clear()
        print("🔄 Conversation cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_latency = (
            self.metrics["total_latency"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0 else 0.0
        )
        return {
            "total_requests": self.metrics["total_requests"],
            "avg_latency": round(avg_latency, 2),
            "errors": self.metrics["errors"],
            "context_messages": len(self.context.messages),
            "estimated_tokens": self.context.estimated_tokens,
        }

    async def close(self):
        """Cleanup resources"""
        await self.client.close()


# Backwards compatibility alias
LocalAgent = OptimizedAgent


# Simple test
if __name__ == "__main__":
    async def test():
        agent = OptimizedAgent()
        print("✅ Agent initialized")
        print(f"   Model: {agent.model}")
        print(f"   Stats: {agent.get_stats()}")

        # Test Ollama connection
        models = await agent.client.list_models()
        print(f"   Available models: {models[:3]}...")

        await agent.close()

    asyncio.run(test())