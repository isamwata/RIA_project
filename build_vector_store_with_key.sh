#!/bin/bash
# Build vector store with OpenAI API key from environment
# 
# IMPORTANT: Set your OpenAI API key as an environment variable before running:
#   export OPENAI_API_KEY="your-api-key-here"
#   Or source set_api_keys.sh which loads keys from environment

# Use API key from environment (set via set_api_keys.sh or export)
# If not set, the script will prompt or fail gracefully
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set in environment"
    echo "   Set it with: export OPENAI_API_KEY='your-key-here'"
    echo "   Or source set_api_keys.sh"
    exit 1
fi

echo "🔑 Using OpenAI API key from environment"
echo "📚 Building vector store with OpenAI embeddings..."
echo ""

python build_vector_store_openai.py
