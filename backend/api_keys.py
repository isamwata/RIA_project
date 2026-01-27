"""Centralized API key management for the RIA Project.

This module ensures API keys are loaded from the environment at import time,
which is critical when running in virtual environments or when environment
variables need to be explicitly loaded.
"""

import os
from typing import Optional

# Try to load from .env file first
# Use absolute path to ensure we load from project root
try:
    from dotenv import load_dotenv
    import os
    from pathlib import Path
    
    # Get project root (parent of backend directory)
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    env_path = project_root / ".env"
    
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        # Fallback: try current directory
        load_dotenv()
except (ImportError, PermissionError, FileNotFoundError) as e:
    # If dotenv fails, continue - keys might be in environment
    pass


def get_api_key(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an API key from environment variables.
    
    This function ensures keys are loaded from the environment, which is
    important when running in virtual environments where environment
    variables might not be automatically inherited.
    
    Args:
        key_name: Name of the environment variable (e.g., "OPENAI_API_KEY")
        default: Default value if key is not found (DEPRECATED - don't use placeholders)
    
    Returns:
        API key value or None
    """
    # First try direct environment variable
    value = os.getenv(key_name)
    
    # If still None, try uppercase version
    if value is None:
        value = os.getenv(key_name.upper())
    
    # Check if value is a placeholder (common placeholder patterns)
    if value:
        placeholder_patterns = [
            "your-", "placeholder", "replace-me", "set-your", 
            "your-openai", "your-anthropic", "your-xai", "your-google"
        ]
        if any(pattern in value.lower() for pattern in placeholder_patterns):
            # This is a placeholder, return None instead
            return None
    
    # Only use default if it's not a placeholder
    if value is None and default is not None:
        if not any(pattern in default.lower() for pattern in placeholder_patterns):
            value = default
    
    return value


# Load all API keys at module import time
OPENAI_API_KEY = get_api_key("OPENAI_API_KEY")
ANTHROPIC_API_KEY = get_api_key("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = get_api_key("GOOGLE_API_KEY")
XAI_API_KEY = get_api_key("XAI_API_KEY")
XAI_API_KEY_ALT = get_api_key("XAI_API_KEY_ALT")
OPENROUTER_API_KEY = get_api_key("OPENROUTER_API_KEY")


def verify_api_keys() -> dict:
    """
    Verify which API keys are available.
    
    Returns:
        Dict with key names and availability status (True/False)
    """
    return {
        "OPENAI_API_KEY": OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 0,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY is not None and len(ANTHROPIC_API_KEY) > 0,
        "GOOGLE_API_KEY": GOOGLE_API_KEY is not None and len(GOOGLE_API_KEY) > 0,
        "XAI_API_KEY": XAI_API_KEY is not None and len(XAI_API_KEY) > 0,
        "XAI_API_KEY_ALT": XAI_API_KEY_ALT is not None and len(XAI_API_KEY_ALT) > 0,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY is not None and len(OPENROUTER_API_KEY) > 0,
    }


def print_api_key_status():
    """Print the status of all API keys (for debugging)."""
    status = verify_api_keys()
    print("\n📋 API Key Status:")
    print("=" * 60)
    for key_name, available in status.items():
        status_icon = "✅" if available else "❌"
        key_value = globals().get(key_name, None)
        if available and key_value:
            # Show first 10 and last 4 chars for verification
            preview = f"{key_value[:10]}...{key_value[-4:]}" if len(key_value) > 14 else "***"
            print(f"   {status_icon} {key_name}: {preview}")
        else:
            print(f"   {status_icon} {key_name}: Not set")
    print("=" * 60)
