#!/bin/bash
# API Keys Configuration Script
# This script sets all API keys as environment variables
# 
# IMPORTANT: Replace the placeholder values below with your actual API keys
# DO NOT commit actual API keys to git - use environment variables or .env file

# OpenAI API Key
export OPENAI_API_KEY="${OPENAI_API_KEY:-your-openai-api-key-here}"

# Anthropic (Claude) API Key
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-your-anthropic-api-key-here}"

# Google (Gemini) API Key
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-your-google-api-key-here}"

# xAI (Grok) API Keys
export XAI_API_KEY="${XAI_API_KEY:-your-xai-api-key-here}"
export XAI_API_KEY_ALT="${XAI_API_KEY_ALT:-your-xai-api-key-alt-here}"

# OpenRouter API Key (if using OpenRouter, can use any of the above keys)
# export OPENROUTER_API_KEY="your-openrouter-key"

echo "✅ API Keys set in environment:"
echo "   - OPENAI_API_KEY"
echo "   - ANTHROPIC_API_KEY"
echo "   - GOOGLE_API_KEY"
echo "   - XAI_API_KEY"
echo "   - XAI_API_KEY_ALT"
echo ""
echo "To use these keys, source this script:"
echo "   source set_api_keys.sh"
echo ""
echo "Or run commands with:"
echo "   source set_api_keys.sh && python your_script.py"
