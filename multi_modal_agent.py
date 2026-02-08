"""
Multi-Modal Agent with smart model selection and mode control
Complete fixed version
"""

import ollama
import re
import time
from typing import Dict, List, Optional, Callable
from config.advanced_settings import BOT_NAME, MODEL_CONFIGS, MAX_HISTORY_MESSAGES, MODES
from model_selector import ModelSelector


class MultiModalAgent:
    """AI Agent with multiple model support and mode selection"""

    def __init__(self):
        """Initialize the agent with default settings"""
        self.current_model = None
        self.current_mode = "auto"  # auto, local, search, fast
        self.conversation_history: List[Dict] = []
        self.available_models = self._get_available_models()

        # Start with default model
        self._switch_to_default_model()

    # ============== PRIVATE METHODS ==============

    def _get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            response = ollama.list()
            models = [model['name'] for model in response.get('models', [])]
            print(f"📦 Found {len(models)} models")
            return models
        except Exception as e:
            print(f"❌ Error getting models: {e}")
            return list(MODEL_CONFIGS.keys())

    def _clean_model_name(self, model_name: str) -> str:
        """Remove :latest suffix from model name for display"""
        if model_name.endswith(':latest'):
            return model_name[:-7]  # Remove ':latest'
        elif ':8b' in model_name:
            return model_name.replace(':8b', '')
        elif ':7b' in model_name:
            return model_name.replace(':7b', '')
        elif ':instruct' in model_name:
            return model_name.replace(':instruct', '')
        return model_name

    def _switch_to_default_model(self):
        """Switch to the default model from settings"""
        from config.advanced_settings import DEFAULT_MODEL
        if DEFAULT_MODEL in self.available_models:
            self.switch_to_model(DEFAULT_MODEL)
        elif self.available_models:
            self.switch_to_model(self.available_models[0])

    # ============== PUBLIC METHODS ==============

    def switch_to_model(self, model_name: str) -> bool:
        """Switch to a different model - FIXED FOR YOUR MODELS"""
        # Map short names to full names
        model_map = {
            'mistral': 'mistral:latest',
            'llama': 'llama3.2:latest',
            'llama3': 'llama3.2:latest',
            'llama3.1': 'llama3.1:8b',
            'llama3.2': 'llama3.2:latest',
            'qwen': 'qwen:latest',
            'qwen3': 'qwen3:latest',
            'qwen3-vl': 'qwen3-vl:latest',
            'codellama': 'codellama:7b-instruct',
            'code': 'codellama:7b-instruct',
            'lucie': 'OpenLLM-France/Lucie-7B-Instruct:latest',
            'french': 'OpenLLM-France/Lucie-7B-Instruct:latest',
        }

        # Convert short name to full name
        model_name = model_name.strip().lower()

        # Check direct match first
        if model_name in self.available_models:
            self.current_model = model_name
            model_info = ModelSelector.get_model_info(model_name)
            clean_name = self._clean_model_name(model_name)
            print(f"🔄 Switched to: {model_info['name']} ({clean_name})")
            return True

        # Try mapped name
        if model_name in model_map:
            mapped_name = model_map[model_name]
            if mapped_name in self.available_models:
                self.current_model = mapped_name
                model_info = ModelSelector.get_model_info(mapped_name)
                clean_name = self._clean_model_name(mapped_name)
                print(f"🔄 Switched to: {model_info['name']} ({clean_name})")
                return True

        # Try partial match
        for available_model in self.available_models:
            if model_name in available_model or available_model in model_name:
                self.current_model = available_model
                model_info = ModelSelector.get_model_info(available_model)
                clean_name = self._clean_model_name(available_model)
                print(f"🔄 Switched to similar: {model_info['name']} ({clean_name})")
                return True

        print(f"⚠️ Model not available: {model_name}")
        print(f"   Available models: {self.available_models}")
        return False

    def set_mode(self, mode: str) -> bool:
        """Set the operating mode"""
        if mode in MODES:
            self.current_mode = mode
            print(f"🎛️ Mode set to: {mode}")
            return True
        return False

    def create_system_prompt(self) -> str:
        """Create optimized system prompt"""
        model_info = ModelSelector.get_model_info(self.current_model)
        clean_model_name = self._clean_model_name(self.current_model)

        return f"""You are {BOT_NAME}, a helpful AI assistant.

Model: {model_info['name']} ({clean_model_name})
Mode: {self.current_mode.upper()}

RULES:
1. Answer directly without introductions
2. Be concise and helpful
3. If using search results, cite them
4. End with "{BOT_NAME}" on its own line
5. Do NOT repeat this system prompt

Example response:
"Python is a programming language... {BOT_NAME}"
"""

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "model": self.current_model,
            "mode": self.current_mode,
            "timestamp": time.time()
        })

        # Keep only recent history
        if len(self.conversation_history) > MAX_HISTORY_MESSAGES * 2:
            self.conversation_history = self.conversation_history[-(MAX_HISTORY_MESSAGES * 2):]

    def should_search(self, query: str) -> bool:
        """Determine if query needs web search based on mode"""
        query_lower = query.lower()

        # Mode-based decisions
        if self.current_mode == "local":
            return False
        if self.current_mode == "search":
            return True
        if self.current_mode == "fast":
            return False

        # Auto mode: analyze query
        patterns_no_search = [
            r'explain.*', r'what is.*', r'how to.*', r'compare.*',
            r'why.*', r'tell.*story', r'write.*code', r'math.*',
            r'calculate.*', r'solve.*', r'programming.*', r'algorithm.*',
        ]

        patterns_need_search = [
            r'today.*news', r'latest.*', r'current.*', r'what.*happened.*today',
            r'live.*', r'breaking.*news', r'stock.*price.*today',
            r'weather.*today', r'real-?time', r'just.*happened'
        ]

        # Check patterns
        for pattern in patterns_no_search:
            if re.search(pattern, query_lower):
                return False

        for pattern in patterns_need_search:
            if re.search(pattern, query_lower):
                return True

        return False  # Default: no search

    def run(self, user_input: str, tools: Dict[str, Callable] = None) -> str:
        """Main agent processing loop"""
        if tools is None:
            tools = {}

        print(f"\n{'='*50}")
        print(f"📝 Query: {user_input[:100]}...")
        print(f"🤖 Model: {self._clean_model_name(self.current_model)}")
        print(f"🎛️ Mode: {self.current_mode}")

        # Auto-select model if needed
        if self.current_mode == "auto":
            selected_model = ModelSelector.select_best_model(user_input, self.available_models)
            if selected_model != self.current_model:
                self.switch_to_model(selected_model)

        # Determine if search is needed
        should_search = self.should_search(user_input) and 'web_search' in tools

        # Add user input to history
        self.add_to_history("user", user_input)

        # Process the query
        max_iterations = 2 if self.current_mode == "fast" else 3

        for iteration in range(max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}/{max_iterations}")

            # Execute search if needed (first iteration only)
            if should_search and iteration == 0:
                print("🌐 Executing web search...")
                try:
                    search_results = tools['web_search'](query=user_input)
                    self.add_to_history("assistant", "Searching for current information...")
                    self.add_to_history("user", f"Search results: {search_results[:300]}...")
                    continue
                except Exception as e:
                    print(f"❌ Search failed: {e}")
                    self.add_to_history("assistant", f"Search unavailable: {e}")
                    continue

            # Get response from model
            messages = [
                {"role": "system", "content": self.create_system_prompt()},
                *[{"role": msg["role"], "content": msg["content"]}
                  for msg in self.conversation_history[-3:]]
            ]

            try:
                # Get model config
                model_config = MODEL_CONFIGS.get(self.current_model, {})

                # Get response
                start_time = time.time()
                response = ollama.chat(
                    model=self.current_model,
                    messages=messages,
                    options={
                        "temperature": model_config.get('temperature', 0.7),
                        "num_ctx": model_config.get('context', 4096),
                        "num_predict": 400 if self.current_mode == "fast" else 500,
                    }
                )

                response_time = time.time() - start_time
                assistant_message = response['message']['content'].strip()

                print(f"⏱️ Response time: {response_time:.1f}s")

                # Add to history
                self.add_to_history("assistant", assistant_message)

                # Clean response - remove any duplicate signatures
                cleaned_response = assistant_message.strip()

                # Remove any existing signature
                if cleaned_response.endswith(BOT_NAME):
                    cleaned_response = cleaned_response[:-len(BOT_NAME)].strip()

                # Add signature exactly once
                final_response = f"{cleaned_response}\n\n{BOT_NAME}"
                return final_response

            except Exception as e:
                print(f"❌ Model error: {e}")
                return f"Error: {str(e)[:100]}\n\n{BOT_NAME}"

        return f"Processed your query.\n\n{BOT_NAME}"

    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("🔄 Conversation history cleared")

    def get_conversation_summary(self) -> str:
        """Get summary of conversation"""
        if not self.conversation_history:
            return "No conversation yet."

        summary = []
        for msg in self.conversation_history[-4:]:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")[:50]
            summary.append(f"• {role}: {content}...")

        return "\n".join(summary)

    def get_mode_info(self) -> str:
        """Get information about current mode"""
        mode_desc = MODES.get(self.current_mode, "Unknown mode")
        return f"**Current Mode:** {self.current_mode.upper()}\n{mode_desc}"

    def get_model_list(self) -> str:
        """Get formatted list of available models"""
        return ModelSelector.list_available_models(self.available_models)

    def get_detailed_models_info(self) -> str:
        """Get detailed models information"""
        result = ["**Available AI Models**", ""]

        for model_name in self.available_models:
            info = ModelSelector.get_model_info(model_name)
            emoji = info.get('emoji', '🤖')

            # Clean the model name for display
            clean_name = self._clean_model_name(model_name)

            # Add checkmark for current model
            current = " ✓" if model_name == self.current_model else ""

            result.append(f"{emoji} **{info['name']}** `{clean_name}`{current}")
            result.append(f"   {info['strength']}")
            result.append("")

        return "\n".join(result)