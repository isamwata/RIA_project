#!/usr/bin/env python3
"""
Query the knowledge graph.

Example queries to demonstrate graph traversal and retrieval.
"""

import sys
from pathlib import Path
from backend.knowledge_graph import KnowledgeGraphBuilder

def main():
    """Run example queries on the knowledge graph."""
    graph_file = Path("knowledge_graph.pkl")
    
    if not graph_file.exists():
        print("❌ Knowledge graph not found. Run build_knowledge_graph.py first.")
        sys.exit(1)
    
    builder = KnowledgeGraphBuilder()
    graph = builder.load_graph(str(graph_file))
    
    print("🔍 Knowledge Graph Query Examples")
    print("=" * 60)
    print()
    
    # Query 1: Get all categories
    print("1. All Policy Categories:")
    categories = [node for node, data in graph.nodes(data=True) if data.get("node_type") == "category"]
    for cat_node in sorted(categories):
        cat_name = graph.nodes[cat_node].get("name", "")
        # Count chunks in this category
        chunk_count = sum(1 for neighbor in graph.successors(cat_node) 
                         if graph.nodes[neighbor].get("node_type") == "chunk")
        print(f"   - {cat_name}: {chunk_count} chunks")
    print()
    
    # Query 2: Get all domains
    print("2. All Domains:")
    domains = [node for node, data in graph.nodes(data=True) if data.get("node_type") == "domain"]
    for domain_node in sorted(domains):
        domain_name = graph.nodes[domain_node].get("name", "")
        # Count connected categories
        cat_count = sum(1 for neighbor in graph.successors(domain_node)
                        if graph.nodes[neighbor].get("node_type") == "category")
        print(f"   - {domain_name}: connected to {cat_count} categories")
    print()
    
    # Query 3: Get analysis patterns
    print("3. Analysis Patterns:")
    patterns = [node for node, data in graph.nodes(data=True) if data.get("node_type") == "analysis_pattern"]
    for pattern_node in sorted(patterns):
        pattern_name = graph.nodes[pattern_node].get("name", "")
        # Count chunks using this pattern
        chunk_count = sum(1 for neighbor in graph.successors(pattern_node)
                         if graph.nodes[neighbor].get("node_type") == "chunk")
        print(f"   - {pattern_name}: used by {chunk_count} chunks")
    print()
    
    # Query 4: Find chunks by category
    print("4. Sample: Chunks in 'Environment' category:")
    env_node = "category:Environment"
    if env_node in graph:
        env_chunks = [neighbor for neighbor in graph.successors(env_node)
                     if graph.nodes[neighbor].get("node_type") == "chunk"]
        print(f"   Found {len(env_chunks)} chunks")
        for i, chunk_node in enumerate(env_chunks[:5], 1):
            chunk_data = graph.nodes[chunk_node]
            chunk_type = chunk_data.get("chunk_type", "")
            chunk_id = chunk_data.get("chunk_id", "")[:60]
            print(f"   {i}. [{chunk_type}] {chunk_id}...")
    print()
    
    # Query 5: Document to chunks relationship
    print("5. Documents and their chunks:")
    documents = [node for node, data in graph.nodes(data=True) if data.get("node_type") == "document"]
    for doc_node in sorted(documents)[:3]:
        doc_name = graph.nodes[doc_node].get("name", "")
        chunk_count = sum(1 for neighbor in graph.successors(doc_node)
                         if graph.nodes[neighbor].get("node_type") == "chunk")
        print(f"   - {doc_name}: {chunk_count} chunks")
    print()
    
    # Query 6: Multi-hop query - Category -> Domain -> Pattern
    print("6. Multi-hop: Environment category -> Domains -> Patterns:")
    env_node = "category:Environment"
    if env_node in graph:
        # Get domains connected to Environment
        domains = [neighbor for neighbor in graph.successors(env_node)
                  if graph.nodes[neighbor].get("node_type") == "domain"]
        for domain_node in domains[:2]:
            domain_name = graph.nodes[domain_node].get("name", "")
            # Get patterns connected to this domain
            patterns = [neighbor for neighbor in graph.successors(domain_node)
                       if graph.nodes[neighbor].get("node_type") == "analysis_pattern"]
            print(f"   {domain_name}: {len(patterns)} patterns")
            for pattern_node in patterns[:3]:
                pattern_name = graph.nodes[pattern_node].get("name", "")
                print(f"     - {pattern_name}")
    print()
    
    # Query 7: Evidence supporting analysis
    print("7. Evidence -> Analysis relationships:")
    evidence_chunks = [node for node, data in graph.nodes(data=True)
                      if data.get("node_type") == "chunk" and data.get("chunk_type") == "evidence"]
    if evidence_chunks:
        sample_evidence = evidence_chunks[0]
        # Find analysis chunks this evidence supports
        analysis_chunks = [neighbor for neighbor in graph.successors(sample_evidence)
                          if graph.nodes[neighbor].get("chunk_type") == "analysis"]
        print(f"   Sample evidence chunk supports {len(analysis_chunks)} analysis chunks")
    print()
    
    print("=" * 60)
    print("✅ Query examples completed!")

if __name__ == "__main__":
    main()
