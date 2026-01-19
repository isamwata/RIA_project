#!/usr/bin/env python3
"""
Build vector store from chunks.

Creates dense embeddings and sparse BM25 index for hybrid retrieval.
"""

import sys
from pathlib import Path
from backend.vector_store import build_vector_store

def main():
    """Build vector store from chunks."""
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
    print(f"🔍 Building vector store with embeddings and BM25...")
    print()
    
    try:
        # Use OpenAI by default (no local model needed)
        from backend.vector_store import VectorStore
        import json
        
        store = VectorStore(use_local_model=False, embedding_model="text-embedding-3-small")
        
        # Load all chunks
        all_chunks = []
        for chunk_file in chunk_files:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunks_data = json.load(f)
                all_chunks.extend(chunks_data.get("chunks", []))
        
        print(f"📥 Adding {len(all_chunks)} chunks to vector store...")
        print(f"   (Using OpenAI embeddings - ensure OPENAI_API_KEY is set)")
        store.add_chunks(all_chunks)
        store.save("vector_store")
        
        print(f"\n✅ Vector store successfully built!")
        print(f"   Vector store directory: vector_store/")
        print(f"   Used OpenAI embeddings (text-embedding-3-small)")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
