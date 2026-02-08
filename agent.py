"""
AI Agent - Core Logic
Handles conversation with Ollama and tool orchestration
Optimized for speed and error handling
"""

import ollama
import json
import re
import threading
import time
from queue import Queue
from typing import Dict, Any, List, Optional, Callable
from config.settings import OLLAMA_MODEL


class LocalAgent:
    """AI Agent that uses Ollama for reasoning and tool execution"""

    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 6  # Reduced for faster performance
        self.tools_description = ""
        self.previous_searches = set()  # Track searches to avoid duplicates

    def create_system_prompt(self) -> str:
        """Create efficient system prompt"""
        tools_desc = self.tools_description or "No tools available. Answer based on your knowledge."

        return f"""You are a helpful AI assistant with access to tools.

Available tools:
{tools_desc}

CRITICAL RULES:
1. Use tools ONLY when you need current/real-time information
2. When using tools, output ONLY valid JSON: {{"tool": "tool_name", "parameters": {{"param": "value"}}}}
3. NO additional text with JSON - JUST the JSON
4. After getting tool results, provide a complete natural answer

BE EFFICIENT:
- Make search queries specific and comprehensive
- If unsure, ask clarifying questions
- Don't search for what you already know

EXAMPLES:
User: "Current weather?"
Assistant: {{"tool": "web_search", "parameters": {{"query": "current weather forecast today"}}}}

User: "What is Python?"
Assistant: Python is a programming language...
"""

    def parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract tool call from LLM response"""
        response = response.strip()

        # Check if response starts and ends with braces
        if response.startswith('{') and response.endswith('}'):
            try:
                tool_call = json.loads(response)
                if isinstance(tool_call, dict) and 'tool' in tool_call:
                    return tool_call
            except json.JSONDecodeError:
                pass

        # Try to find JSON in text
        try:
            json_match = re.search(r'\{[^}]*\}', response)
            if json_match:
                tool_call = json.loads(json_match.group())
                if isinstance(tool_call, dict) and 'tool' in tool_call:
                    return tool_call
        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

        # Keep only recent history
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-(self.max_history * 2):]

    def update_tools_description(self, tools: Dict[str, Callable]):
        """Update tools description in system prompt"""
        if not tools:
            self.tools_description = "No tools available."
            return

        descriptions = []
        for tool_name, tool_func in tools.items():
            doc = getattr(tool_func, '__doc__', '') or "No description"
            first_line = doc.strip().split('\n')[0]
            descriptions.append(f"- {tool_name}: {first_line[:100]}")

        self.tools_description = "\n".join(descriptions)

    def execute_tool_with_timeout(self, tool_func: Callable, params: Dict, timeout: int = 8):
        """Execute tool with timeout protection"""
        result_queue = Queue()

        def worker():
            try:
                result = tool_func(**params)
                result_queue.put(('success', result))
            except Exception as e:
                result_queue.put(('error', str(e)))

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            return 'timeout', "Tool execution timed out"

        if result_queue.empty():
            return 'error', "Tool execution failed"

        return result_queue.get()

    def run(self, user_input: str, tools: Dict[str, Callable] = None) -> str:
        """
        Main agent loop - optimized for speed
        """
        if tools is None:
            tools = {}

        # Reset duplicate search tracking for new conversation
        if len(self.conversation_history) == 0:
            self.previous_searches.clear()

        # Update tools description
        self.update_tools_description(tools)

        # Add user input to history
        self.add_to_history("user", user_input)

        # Maximum iterations
        max_iterations = 3  # Reduced for speed

        for iteration in range(max_iterations):
            print(f"🔄 Iteration {iteration + 1}/{max_iterations}")

            # Prepare messages (only recent context)
            recent_history = self.conversation_history[-3:] if len(self.conversation_history) > 3 else self.conversation_history
            messages = [
                {"role": "system", "content": self.create_system_prompt()},
                *recent_history
            ]

            try:
                # Get response from Ollama with timeout
                start_time = time.time()
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": 0.7,
                        "num_ctx": 2048,  # Reduced context
                        "num_predict": 250,  # Limit response length
                    }
                )
                ollama_time = time.time() - start_time
                print(f"🤖 Ollama response: {ollama_time:.1f}s")

                assistant_message = response['message']['content'].strip()

                # Log truncated response
                log_msg = assistant_message[:80] + "..." if len(assistant_message) > 80 else assistant_message
                print(f"🤖 Response: {log_msg}")

                # Check for tool call
                tool_call = self.parse_tool_call(assistant_message)

                if tool_call and tool_call.get('tool') in tools:
                    # Execute the tool
                    tool_name = tool_call['tool']
                    params = tool_call.get('parameters', {})

                    # Check for duplicate web searches
                    if tool_name == 'web_search':
                        query = params.get('query', '').lower().strip()
                        if query in self.previous_searches:
                            print(f"⚠️ Duplicate search skipped: {query}")
                            self.add_to_history("assistant", assistant_message)
                            self.add_to_history("user", "Already searched for this. Please answer with available information.")
                            continue
                        self.previous_searches.add(query)

                    print(f"🔧 Executing: {tool_name}")

                    # Execute with timeout
                    status, tool_result = self.execute_tool_with_timeout(
                        tools[tool_name], params, timeout=10
                    )

                    if status == 'timeout':
                        error_msg = f"Tool '{tool_name}' timed out"
                        print(f"❌ {error_msg}")
                        self.add_to_history("assistant", assistant_message)
                        self.add_to_history("user", error_msg)
                        continue
                    elif status == 'error':
                        error_msg = f"Tool error: {tool_result[:100]}"
                        print(f"❌ {error_msg}")
                        self.add_to_history("assistant", assistant_message)
                        self.add_to_history("user", error_msg)
                        continue

                    # Truncate very long results
                    if len(str(tool_result)) > 1500:
                        tool_result = str(tool_result)[:1500] + "... [truncated]"

                    # Add to history
                    self.add_to_history("assistant", assistant_message)
                    self.add_to_history("user", f"Tool result: {tool_result}")

                    # Continue to next iteration
                    continue

                elif tool_call:
                    # Tool call but tool not available
                    tool_name = tool_call.get('tool', 'unknown')

                    if tool_name not in tools:
                        # Try to extract clean response
                        clean_response = re.sub(r'\{[^}]*\}', '', assistant_message).strip()
                        if clean_response:
                            print(f"⚠️ Tool '{tool_name}' not available, using text")
                            self.add_to_history("assistant", clean_response)
                            return clean_response

                    # Ask AI to answer directly
                    fallback = f"Tool '{tool_name}' unavailable. Please answer directly."
                    self.add_to_history("user", fallback)
                    continue

                else:
                    # No tool call - final response
                    self.add_to_history("assistant", assistant_message)
                    return assistant_message

            except Exception as e:
                error_msg = f"Error: {str(e)[:100]}"
                print(f"❌ {error_msg}")
                return f"I encountered an error: {error_msg}"

        # Max iterations reached
        return "I've tried multiple approaches. Could you rephrase your question or ask something more specific?"

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.previous_searches.clear()
        print("🔄 Conversation cleared")

    def get_conversation_length(self) -> int:
        """Get number of messages in history"""
        return len(self.conversation_history)