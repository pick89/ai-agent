#!/usr/bin/env python3
"""
Verify all fixes are in place
"""

import sys
import os

print("🔍 Verifying fixes...")

# Check 1: multi_modal_agent.py has reset_conversation
with open('multi_modal_agent.py', 'r') as f:
    content = f.read()
    if 'def reset_conversation' in content:
        print("✅ multi_modal_agent.py has reset_conversation method")
    else:
        print("❌ reset_conversation missing!")

# Check 2: advanced_settings.py has correct bot name
with open('config/advanced_settings.py', 'r') as f:
    content = f.read()
    if 'BOT_NAME = "Buddy 🤖✨"' in content:
        print("✅ advanced_settings.py has correct BOT_NAME")
    else:
        print("❌ BOT_NAME incorrect!")

# Check 3: Test import
try:
    from multi_modal_agent import MultiModalAgent

    print("✅ MultiModalAgent imports successfully")

    # Test instantiation
    agent = MultiModalAgent()
    print(f"✅ Agent created. Current model: {agent.current_model}")

    # Test reset
    try:
        agent.reset_conversation()
        print("✅ reset_conversation() works")
    except Exception as e:
        print(f"❌ reset_conversation() failed: {e}")

    # Test model switching
    try:
        success = agent.switch_to_model('codellama')
        print(f"✅ switch_to_model('codellama'): {success}")
    except Exception as e:
        print(f"❌ switch_to_model failed: {e}")

except Exception as e:
    print(f"❌ Import/instantiation failed: {e}")

print("\n🎯 Verification complete!")