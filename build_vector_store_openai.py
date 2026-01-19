#!/usr/bin/env python3
"""
Build vector store from chunks using OpenAI embeddings.
Use this if sentence-transformers has Keras compatibility issues.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
    print("⚠️  No OpenAI API key found!")
    print("   Set OPENAI_API_KEY or OPENROUTER_API_KEY in .env file")
    print("   Or install tf-keras to use local embeddings:")
    print("     pip install tf-keras")
    sys.exit(1)

def main():
    """Build vector store from chunks using OpenAI."""
    chunks_dir = Path("chunks")
    
    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        print("   Run Stage 2 first to generate chunks.")
        sys.exit(1)
    
    chunk_files = list(chunks_dir.glob("*_chunks.json"))
    if not chunk_files:
        print(f"❌ No chunk files found in {chunks_dir}/")
        sys.exit(1)
    
    print(f"📚 Found {len(chunk_files)} chunk file(s)")
    print(f"🔍 Building vector store with OpenAI embeddings and BM25...")
    print(f"   (This will use OpenAI API - ensure you have credits)")
    print()
    
    try:
        # Import and modify to use OpenAI
        from backend.vector_store import VectorStore
        import json
        
        # Initialize with OpenAI (not local model)
        print("📦 Initializing VectorStore with OpenAI embeddings...")
        store = VectorStore(use_local_model=False, embedding_model="text-embedding-3-small")
        
        # Load all chunks
        all_chunks = []
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
                all_chunks.extend(chunks_data.get("chunks", []))
        
        print(f"📥 Adding {len(all_chunks)} chunks to vector store...")
        print(f"   (This may take a few minutes - generating embeddings via API)")
        store.add_chunks(all_chunks)
        
        # Save vector store
        print(f"💾 Saving vector store...")
        store.save("vector_store")
        
        print(f"\n✅ Vector store successfully built!")
        print(f"   Vector store directory: vector_store/")
        print(f"   Used OpenAI embeddings (text-embed-3-small)")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
