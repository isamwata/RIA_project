"""Direct API clients for Anthropic, Google, and xAI (bypassing OpenRouter)."""

import os
import httpx
from typing import List, Dict, Any, Optional
import asyncio

# Import API keys from centralized module
try:
    from .api_keys import (
        ANTHROPIC_API_KEY,
        GOOGLE_API_KEY,
        XAI_API_KEY,
        OPENAI_API_KEY
    )
except ImportError:
    # Fallback to direct environment access
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    XAI_API_KEY = os.getenv("XAI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


async def query_anthropic(
    messages: List[Dict[str, str]],
    model: str = "claude-sonnet-4-20250514",
    timeout: float = 300.0  # Increased to 5 minutes for long RIA assessments
) -> Optional[Dict[str, Any]]:
    """Query Anthropic Claude API directly."""
    if not ANTHROPIC_API_KEY:
        print(f"⚠️  ANTHROPIC_API_KEY not set - cannot query Anthropic")
        return None
    
    # Convert messages to Anthropic format
    system_message = None
    anthropic_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
        else:
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": 8192  # Increased for comprehensive RIA reports
    }
    
    if system_message:
        payload["system"] = system_message
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'content': data['content'][0]['text'],
                'model': model
            }
    except httpx.HTTPStatusError as e:
        print(f"Error querying Anthropic {model}: HTTP {e.response.status_code}")
        try:
            error_data = e.response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            print(f"   Error details: {error_msg}")
        except:
            print(f"   Response: {e.response.text[:200]}")
        return None
    except Exception as e:
        print(f"Error querying Anthropic {model}: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None


async def query_google(
    messages: List[Dict[str, str]],
    model: str = "gemini-2.0-flash-exp",
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query Google Gemini API directly."""
    if not GOOGLE_API_KEY:
        print(f"⚠️  GOOGLE_API_KEY not set - cannot query Google")
        return None
    
    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": contents
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return {
                'content': data['candidates'][0]['content']['parts'][0]['text'],
                'model': model
            }
    except Exception as e:
        print(f"Error querying Google {model}: {e}")
        return None


async def query_xai(
    messages: List[Dict[str, str]],
    model: str = "grok-2-1212",
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query xAI Grok API directly."""
    if not XAI_API_KEY:
        print(f"⚠️  XAI_API_KEY not set - cannot query xAI")
        return None
    
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                'content': data['choices'][0]['message']['content'],
                'model': model
            }
    except httpx.ConnectError as e:
        print(f"Error querying xAI {model}: Connection/DNS failed - {e}")
        print(f"   This might indicate a network connectivity or DNS resolution issue")
        print(f"   Check your internet connection and DNS settings")
        return None
    except httpx.HTTPStatusError as e:
        print(f"Error querying xAI {model}: HTTP {e.response.status_code}")
        try:
            error_data = e.response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            print(f"   Error details: {error_msg}")
        except:
            pass
        return None
    except Exception as e:
        print(f"Error querying xAI {model}: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None


async def query_openai(
    messages: List[Dict[str, str]],
    model: str = "gpt-4",
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """Query OpenAI API directly."""
    if not OPENAI_API_KEY:
        print(f"⚠️  OPENAI_API_KEY not set - cannot query OpenAI")
        return None
    
    # Debug: Show partial key for verification (first 7 chars, which is standard for OpenAI keys)
    key_preview = f"{OPENAI_API_KEY[:7]}..." if len(OPENAI_API_KEY) > 7 else "***"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096  # Reduced to fit within model's context window
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            # Better error handling
            if response.status_code == 401:
                print(f"❌ OpenAI API authentication failed (401)")
                print(f"   Key preview: {key_preview}")
                print(f"   Key length: {len(OPENAI_API_KEY)} chars")
                print(f"   Please verify your OPENAI_API_KEY is correct and active")
                response.raise_for_status()
            elif response.status_code == 429:
                print(f"⚠️  OpenAI API rate limit exceeded (429) - please wait")
                response.raise_for_status()
            else:
                response.raise_for_status()
            
            data = response.json()
            
            return {
                'content': data['choices'][0]['message']['content'],
                'model': model
            }
    except httpx.HTTPStatusError as e:
        print(f"Error querying OpenAI {model}: HTTP {e.response.status_code}")
        if e.response.status_code == 401:
            print(f"   Authentication failed - check your API key")
        elif e.response.status_code == 400:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                print(f"   Bad Request (400): {error_msg}")
                print(f"   This might indicate an invalid model name or request format")
                print(f"   Model used: {model}")
            except:
                print(f"   Bad Request (400) - check model name and request format")
        elif e.response.status_code == 404:
            print(f"   Model not found (404) - check if '{model}' is a valid OpenAI model")
        else:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                print(f"   Error details: {error_msg}")
            except:
                pass
        return None
    except httpx.ConnectError as e:
        print(f"Error querying OpenAI {model}: Connection failed - {e}")
        print(f"   This might indicate a network connectivity issue")
        return None
    except Exception as e:
        print(f"Error querying OpenAI {model}: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None


# Model identifier to API function mapping
MODEL_TO_API = {
    "anthropic/claude-sonnet-4-20250514": query_anthropic,
    "anthropic/claude-sonnet-4.5": query_anthropic,
    "anthropic/claude-opus-4": query_anthropic,
    "google/gemini-2.0-flash-exp": query_google,
    "google/gemini-3-pro-preview": query_google,
    "x-ai/grok-2-1212": query_xai,
    "x-ai/grok-4": query_xai,
    "openai/gpt-4": query_openai,
    "openai/gpt-4o": query_openai,
    "openai/gpt-5.1": query_openai,
}


async def query_model_direct(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a model using direct API calls (bypassing OpenRouter).
    
    Args:
        model: Model identifier (e.g., "anthropic/claude-sonnet-4.5")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
    
    Returns:
        Response dict with 'content' and 'model', or None if failed
    """
    # Map model identifier to API function
    api_func = None
    api_model = model
    
    # Handle model identifier mapping
    if model.startswith("anthropic/"):
        api_func = query_anthropic
        # Extract model name (e.g., "claude-sonnet-4.5" from "anthropic/claude-sonnet-4.5")
        api_model = model.split("/")[1] if "/" in model else "claude-sonnet-4-20250514"
    elif model.startswith("google/"):
        api_func = query_google
        api_model = model.split("/")[1] if "/" in model else "gemini-2.0-flash-exp"
    elif model.startswith("x-ai/"):
        api_func = query_xai
        api_model = model.split("/")[1] if "/" in model else "grok-2-1212"
    elif model.startswith("openai/"):
        api_func = query_openai
        api_model = model.split("/")[1] if "/" in model else "gpt-4"
    else:
        # Try direct lookup
        api_func = MODEL_TO_API.get(model)
        if not api_func:
            print(f"Unknown model: {model}, trying OpenAI fallback")
            api_func = query_openai
            api_model = "gpt-4"
    
    if api_func:
        return await api_func(messages, model=api_model, timeout=timeout)
    
    return None


async def query_models_parallel_direct(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel using direct APIs.
    
    Args:
        models: List of model identifiers
        messages: List of message dicts to send to each model
    
    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    # Create tasks for all models
    tasks = [query_model_direct(model, messages) for model in models]
    
    # Wait for all to complete
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Map models to their responses (handle exceptions)
    result = {}
    for model, response in zip(models, responses):
        if isinstance(response, Exception):
            print(f"Exception querying {model}: {response}")
            result[model] = None
        else:
            result[model] = response
    
    return result
