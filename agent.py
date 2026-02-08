"""
AI Agent - Core Logic
Handles conversation with Ollama and tool orchestration
"""

import ollama
import json
import re
import traceback
from typing import Dict, Any, List, Optional, Callable
from config.settings import OLLAMA_MODEL


class LocalAgent:
    """AI Agent that uses Ollama for reasoning and tool execution"""
    
    def __init__(self, model: str = OLLAMA_MODEL):
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10  # Keep last 10 messages to save memory
        self.tools_description = ""
        
    def create_system_prompt(self) -> str:
        """Create the system prompt that defines agent capabilities"""
        tools_desc = self.tools_description or "No tools available. Answer based on your knowledge."
        
        return f"""You are a helpful AI assistant with access to tools.

Available tools:
{tools_desc}

STRICT RULES - FOLLOW EXACTLY:

1. When you need current/recent information that you don't have, use appropriate tools
2. When using a tool: Output ONLY the JSON, absolutely nothing else
3. Tool JSON format: {{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}
4. After tool results come back, synthesize them into a natural answer
5. If you already know the answer, respond naturally without any JSON

EXAMPLES:

User: "What is Python?"
Assistant: Python is a high-level programming language...
(No tool needed - you know this)

User: "What happened in AI news today?"
Assistant: {{"tool": "web_search", "parameters": {{"query": "AI news today"}}}}
(Tool needed - ONLY JSON, nothing else)

User: "Tool 'web_search' result: Latest AI breakthroughs..."
Assistant: Based on the latest news, here's what's happening in AI...
(Natural response after getting tool results)

CRITICAL: NEVER output JSON and text together. It must be one or the other."""

    def parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract tool call from LLM response if present"""
        try:
            # Look for JSON in the response (more robust pattern)
            json_match = re.search(r'\{[\s\S]*\}', response.strip())
            if json_match:
                tool_call = json.loads(json_match.group())
                if 'tool' in tool_call:
                    return tool_call
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"⚠️ Failed to parse tool call: {e}")
            print(f"Response was: {response[:100]}...")
        return None

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Keep only recent history to save memory
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-(self.max_history * 2):]

    def update_tools_description(self, tools: Dict[str, Callable]):
        """Update tools description in system prompt"""
        if not tools:
            self.tools_description = "No tools available. Answer based on your knowledge."
            return
        
        descriptions = []
        for tool_name, tool_func in tools.items():
            # Try to get docstring for better description
            doc = tool_func.__doc__ or "No description available"
            # Clean docstring (first line only)
            clean_doc = doc.strip().split('\n')[0]
            descriptions.append(f"- {tool_name}: {clean_doc}")
        
        self.tools_description = "\n".join(descriptions)

    def run(self, user_input: str, tools: Dict[str, Callable] = None) -> str:
        """
        Main agent loop - processes user input and executes tools if needed
        
        Args:
            user_input: The user's message
            tools: Dictionary of available tools {tool_name: function}
            
        Returns:
            Agent's response as a string
        """
        if tools is None:
            tools = {}
        
        # Update tools description for system prompt
        self.update_tools_description(tools)
        
        # Add user input to history
        self.add_to_history("user", user_input)
        
        # Maximum iterations to prevent infinite loops
        max_iterations = 5
        
        for iteration in range(max_iterations):
            print(f"\n🔄 Agent iteration {iteration + 1}/{max_iterations}")
            
            # Prepare messages for Ollama
            messages = [
                {"role": "system", "content": self.create_system_prompt()},
                *self.conversation_history
            ]
            
            try:
                # Get response from Ollama
                print("🤖 Querying Ollama...")
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": 0.7,
                        "num_ctx": 4096,  # Context window
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                    }
                )
                
                assistant_message = response['message']['content'].strip()
                print(f"🤖 Assistant raw response: {assistant_message[:100]}...")
                
                # Check if there's a tool call
                tool_call = self.parse_tool_call(assistant_message)
                
                if tool_call and tool_call.get('tool') in tools:
                    # Execute the tool
                    tool_name = tool_call['tool']
                    params = tool_call.get('parameters', {})
                    
                    print(f"🔧 Executing tool: {tool_name} with params: {params}")
                    
                    try:
                        # Execute the tool
                        tool_result = tools[tool_name](**params)
                        
                        # Add tool execution to history
                        self.add_to_history("assistant", assistant_message)
                        self.add_to_history("user", f"Tool '{tool_name}' result: {tool_result}")
                        
                        # Continue loop to get final response
                        continue
                        
                    except Exception as e:
                        error_msg = f"Tool execution error: {str(e)}"
                        print(f"❌ {error_msg}")
                        traceback.print_exc()
                        
                        self.add_to_history("assistant", assistant_message)
                        self.add_to_history("user", error_msg)
                        continue
                        
                elif tool_call:
                    # Tool call detected but tool not available OR
                    # AI included both JSON and text (which it shouldn't)
                    
                    tool_name = tool_call.get('tool')
                    
                    if tool_name not in tools:
                        # Tool doesn't exist - strip JSON and return text
                        clean_response = re.sub(r'\{[\s\S]*\}', '', assistant_message).strip()
                        
                        if clean_response:
                            print(f"⚠️ Tool '{tool_name}' not available. Using cleaned response.")
                            self.add_to_history("assistant", clean_response)
                            return clean_response
                        else:
                            # Only had JSON for unavailable tool
                            fallback = f"The tool '{tool_name}' is not available. Please answer based on your knowledge."
                            print(f"⚠️ {fallback}")
                            self.add_to_history("user", fallback)
                            continue
                    else:
                        # Tool exists but AI also included text (breaking rules)
                        # Execute the tool anyway
                        params = tool_call.get('parameters', {})
                        print(f"🔧 Executing tool (AI broke rules): {tool_name}")
                        
                        try:
                            tool_result = tools[tool_name](**params)
                            # Use clean JSON instead of assistant's broken message
                            clean_json = json.dumps({"tool": tool_name, "parameters": params})
                            self.add_to_history("assistant", clean_json)
                            self.add_to_history("user", f"Tool '{tool_name}' result: {tool_result}")
                            continue
                        except Exception as e:
                            error_msg = f"Tool execution error: {str(e)}"
                            print(f"❌ {error_msg}")
                            self.add_to_history("assistant", assistant_message)
                            self.add_to_history("user", error_msg)
                            continue
                else:
                    # No tool call - this is the final response
                    print(f"✨ Final response: {assistant_message[:100]}...")
                    self.add_to_history("assistant", assistant_message)
                    return assistant_message
                    
            except Exception as e:
                error_msg = f"❌ Error communicating with Ollama: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                return error_msg
        
        # If we hit max iterations
        error_msg = "⚠️ Max iterations reached. Please try rephrasing your request."
        print(error_msg)
        return error_msg

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("🔄 Conversation history cleared")

    def get_conversation_length(self) -> int:
        """Get number of messages in history"""
        return len(self.conversation_history)

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation"""
        if not self.conversation_history:
            return "No conversation history."
        
        summary = []
        for i, msg in enumerate(self.conversation_history[-5:]):  # Last 5 messages
            role = msg["role"]
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            summary.append(f"{i+1}. {role}: {content}")
        
        return "\n".join(summary)
