"""
Smart Model Selector
Updated for your actual models
"""

import re
from typing import Dict, List
from config.advanced_settings import MODEL_CONFIGS


class ModelSelector:
    """Intelligently selects the best model for each query"""

    # Query patterns and preferred models - UPDATED FOR YOUR MODELS
    PATTERN_MODEL_MAPPING = {
        # Coding queries
        r'(code|program|function|algorithm|debug|error|syntax)': 'codellama:7b-instruct',
        r'(python|javascript|java|c\+\+|html|css|react|vue|flutter)': 'codellama:7b-instruct',

        # Math and logic
        r'(math|calculate|equation|formula|statistic|probability)': 'qwen3:latest',
        r'(solve|compute|derivative|integral|matrix)': 'qwen3:latest',

        # French language
        r'(français|french|paris|france|bonjour|merci)': 'OpenLLM-France/Lucie-7B-Instruct:latest',

        # Creative writing
        r'(write.*story|poem|creative|fiction|narrative|describe)': 'llama3.2:latest',

        # Analysis and reasoning
        r'(analyze|compare|explain.*detail|why.*how|reasoning)': 'mistral:latest',

        # General multilingual
        r'(中文|español|deutsch|italiano|português|multilingual)': 'qwen3:latest',

        # Vision/image (if we add image support)
        r'(image|picture|photo|drawing|visual|see|look at)': 'qwen3-vl:latest',
    }

    @classmethod
    def select_best_model(cls, query: str, available_models: List[str]) -> str:
        """Select the best model based on query content"""
        query_lower = query.lower()

        # Check against patterns
        for pattern, preferred_model in cls.PATTERN_MODEL_MAPPING.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                if preferred_model in available_models:
                    print(f"🎯 Selected: {cls._get_model_display_name(preferred_model)}")
                    return preferred_model

        # Default logic
        if len(query.split()) > 15:  # Long/complex query
            if 'qwen3:latest' in available_models:
                return 'qwen3:latest'  # Good for complex reasoning

        # Check for general categories
        if '?' in query and len(query.split()) > 8:  # Detailed question
            if 'mistral:latest' in available_models:
                return 'mistral:latest'

        # Default fallback to first available model
        if available_models:
            return available_models[0]

        # Last resort
        from config.advanced_settings import DEFAULT_MODEL
        return DEFAULT_MODEL

    @classmethod
    def get_model_info(cls, model_name: str) -> Dict:
        """Get information about a specific model"""
        info = MODEL_CONFIGS.get(model_name, {
            "name": model_name.split(':')[0].replace('-', ' ').title(),
            "strength": "General purpose",
            "context": 4096,
            "temperature": 0.7,
            "emoji": "🤖"
        })

        # Ensure all required fields exist
        info.setdefault('emoji', '🤖')
        info.setdefault('best_for', ['general'])

        return info

    @classmethod
    def list_available_models(cls, available_models: List[str]) -> str:
        """Create a clean formatted list of available models"""
        result = []
        for model in available_models:
            info = cls.get_model_info(model)
            display_name = cls._get_model_display_name(model)
            result.append(f"• {info.get('emoji', '🤖')} **{info['name']}** (`{display_name}`)")
        return "\n".join(result)

    @classmethod
    def _get_model_display_name(cls, model_name: str) -> str:
        """Get clean display name for model"""
        # Remove :latest
        if model_name.endswith(':latest'):
            return model_name[:-7]
        # Remove version numbers for display
        elif ':8b' in model_name:
            return model_name.replace(':8b', '')
        elif ':7b' in model_name:
            return model_name.replace(':7b', '')
        elif ':instruct' in model_name:
            return model_name.replace(':instruct', '')
        return model_name