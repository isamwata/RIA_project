#!/usr/bin/env python3
"""
Query the vector store.

Demonstrates hybrid search with dense embeddings and sparse BM25.
"""

import sys
from backend.vector_store import VectorStore

def main():
    """Run example queries on the vector store."""
    store = VectorStore(use_local_model=True)
    
    try:
        store.load("vector_store")
    except FileNotFoundError:
        print("❌ Vector store not found. Run build_vector_store.py first.")
        sys.exit(1)
    
    print("🔍 Vector Store Query Examples")
    print("=" * 60)
    print()
    
    # Query 1: Semantic search
    print("1. Semantic Search (Dense Embeddings):")
    print("   Query: 'environmental impact of nature restoration'")
    results = store.search(
        "environmental impact of nature restoration",
        top_k=5,
        use_hybrid=False  # Dense only
    )
    for i, result in enumerate(results, 1):
        print(f"   {i}. Score: {result['score']:.4f}")
        print(f"      Chunk: {result['chunk_id'][:60]}...")
        print(f"      Category: {result['metadata'].get('category', 'N/A')}")
    print()
    
    # Query 2: Keyword search (BM25)
    print("2. Keyword Search (BM25 Sparse Vectors):")
    print("   Query: 'biodiversity ecosystem restoration'")
    results = store.search(
        "biodiversity ecosystem restoration",
        top_k=5,
        use_hybrid=False,
        dense_weight=0.0,
        sparse_weight=1.0
    )
    for i, result in enumerate(results, 1):
        print(f"   {i}. Score: {result['score']:.4f} (sparse: {result['sparse_score']:.4f})")
        print(f"      Chunk: {result['chunk_id'][:60]}...")
    print()
    
    # Query 3: Hybrid search
    print("3. Hybrid Search (Dense + Sparse):")
    print("   Query: 'administrative burdens for SMEs'")
    results = store.search(
        "administrative burdens for SMEs",
        top_k=5,
        use_hybrid=True,
        dense_weight=0.7,
        sparse_weight=0.3
    )
    for i, result in enumerate(results, 1):
        print(f"   {i}. Score: {result['score']:.4f} (dense: {result['dense_score']:.4f}, sparse: {result['sparse_score']:.4f})")
        print(f"      Chunk: {result['chunk_id'][:60]}...")
    print()
    
    # Query 4: Metadata filtering
    print("4. Metadata Filtering:")
    print("   Query: 'impact assessment'")
    print("   Filter: jurisdiction=EU, category=Environment")
    results = store.search(
        "impact assessment",
        top_k=5,
        filter_metadata={
            "jurisdiction": "EU",
            "categories": "Environment"  # Will check if "Environment" in categories list
        }
    )
    for i, result in enumerate(results, 1):
        print(f"   {i}. Score: {result['score']:.4f}")
        print(f"      Jurisdiction: {result['metadata'].get('jurisdiction', 'N/A')}")
        print(f"      Categories: {result['metadata'].get('categories', 'N/A')}")
        print(f"      Chunk: {result['chunk_id'][:60]}...")
    print()
    
    # Query 5: Filter by year
    print("5. Filter by Year:")
    print("   Query: 'policy options'")
    print("   Filter: year=2022")
    results = store.search(
        "policy options",
        top_k=5,
        filter_metadata={"year": "2022"}
    )
    for i, result in enumerate(results, 1):
        print(f"   {i}. Score: {result['score']:.4f}")
        print(f"      Year: {result['metadata'].get('year', 'N/A')}")
        print(f"      Chunk: {result['chunk_id'][:60]}...")
    print()
    
    print("=" * 60)
    print("✅ Query examples completed!")

if __name__ == "__main__":
    main()
