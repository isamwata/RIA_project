"""
Knowledge Graph Builder - Stage 3 (NetworkX)

Builds explicit relationships between concepts, domains, and analytical patterns.
Uses NetworkX for in-memory graph representation.
"""

import json
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import pickle


class KnowledgeGraphBuilder:
    """Builds knowledge graph from chunks using NetworkX."""
    
    # Domain types
    DOMAIN_TYPES = [
        "legal",
        "economic",
        "technological",
        "social",
        "environmental",
        "administrative"
    ]
    
    # Analysis patterns
    ANALYSIS_PATTERNS = [
        "cost_benefit",
        "risk_based",
        "market_failure",
        "stakeholder_analysis",
        "impact_assessment",
        "baseline_comparison",
        "subsidiarity_analysis"
    ]
    
    # Domain mappings (category → domains)
    CATEGORY_TO_DOMAINS = {
        "Environment": ["environmental", "legal", "economic"],
        "Digital": ["technological", "legal", "economic"],
        "Competition": ["economic", "legal"],
        "Health": ["social", "legal", "economic"],
        "Fundamental Rights": ["legal", "social"],
        "Employment": ["economic", "social", "legal"],
        "Economic Development": ["economic", "legal"],
        "Energy": ["environmental", "economic", "technological"],
        "Transport": ["economic", "environmental", "technological"],
        "Agriculture": ["economic", "environmental", "social"],
        "Education": ["social", "economic"],
        "Research & Innovation": ["technological", "economic"],
        "Public Administration": ["administrative", "legal"],
        "International Relations": ["legal", "economic", "social"],
        "Social Cohesion": ["social", "legal"]
    }
    
    # Analysis pattern mappings (analysis_type → patterns)
    ANALYSIS_TYPE_TO_PATTERNS = {
        "problem_definition": ["risk_based", "market_failure"],
        "policy_option": ["cost_benefit", "baseline_comparison"],
        "impact_assessment": ["impact_assessment", "stakeholder_analysis"],
        "baseline": ["baseline_comparison"],
        "administrative_burdens": ["cost_benefit"],
        "stakeholder_analysis": ["stakeholder_analysis"],
        "cost_benefit_analysis": ["cost_benefit"],
        "subsidiarity_proportionality": ["subsidiarity_analysis"]
    }
    
    def __init__(self):
        """Initialize knowledge graph builder."""
        self.graph = nx.MultiDiGraph()  # MultiDiGraph for multiple relationship types
        self.node_counters = {
            "category": 0,
            "domain": 0,
            "analysis_pattern": 0,
            "document": 0,
            "chunk": 0
        }
    
    def build_from_chunks(self, chunks_dir: str = "chunks") -> nx.MultiDiGraph:
        """
        Build knowledge graph from chunk files.
        
        Args:
            chunks_dir: Directory containing chunk JSON files
        
        Returns:
            NetworkX MultiDiGraph
        """
        chunks_path = Path(chunks_dir)
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")
        
        chunk_files = list(chunks_path.glob("*_chunks.json"))
        
        if not chunk_files:
            raise ValueError(f"No chunk files found in {chunks_dir}")
        
        print(f"📊 Building knowledge graph from {len(chunk_files)} chunk file(s)...")
        
        # Step 1: Create all category nodes
        self._create_category_nodes()
        
        # Step 2: Create domain nodes and link to categories
        self._create_domain_nodes()
        
        # Step 3: Create analysis pattern nodes
        self._create_analysis_pattern_nodes()
        
        # Step 4: Process each chunk file
        for chunk_file in chunk_files:
            self._process_chunk_file(chunk_file)
        
        print(f"✅ Knowledge graph built:")
        print(f"   Nodes: {self.graph.number_of_nodes()}")
        print(f"   Edges: {self.graph.number_of_edges()}")
        
        return self.graph
    
    def _create_category_nodes(self):
        """Create category nodes for all policy categories."""
        from backend.chunking_engine import PolicyCategoryMapper
        
        categories = PolicyCategoryMapper.POLICY_CATEGORIES
        
        for category in categories:
            node_id = f"category:{category}"
            self.graph.add_node(
                node_id,
                node_type="category",
                name=category,
                label=category
            )
            self.node_counters["category"] += 1
    
    def _create_domain_nodes(self):
        """Create domain nodes and link them to categories."""
        # Create domain nodes
        for domain_type in self.DOMAIN_TYPES:
            node_id = f"domain:{domain_type}"
            self.graph.add_node(
                node_id,
                node_type="domain",
                domain_type=domain_type,
                name=domain_type.capitalize(),
                label=f"{domain_type.capitalize()} Domain"
            )
            self.node_counters["domain"] += 1
        
        # Link categories to domains
        for category, domains in self.CATEGORY_TO_DOMAINS.items():
            category_node = f"category:{category}"
            if category_node in self.graph:
                for domain_type in domains:
                    domain_node = f"domain:{domain_type}"
                    if domain_node in self.graph:
                        self.graph.add_edge(
                            category_node,
                            domain_node,
                            relationship_type="has_domain",
                            weight=1.0
                        )
                        # Bidirectional relationship
                        self.graph.add_edge(
                            domain_node,
                            category_node,
                            relationship_type="belongs_to_category",
                            weight=1.0
                        )
    
    def _create_analysis_pattern_nodes(self):
        """Create analysis pattern nodes and link them to domains."""
        # Create analysis pattern nodes
        for pattern in self.ANALYSIS_PATTERNS:
            node_id = f"pattern:{pattern}"
            self.graph.add_node(
                node_id,
                node_type="analysis_pattern",
                pattern_type=pattern,
                name=pattern.replace("_", " ").title(),
                label=f"{pattern.replace('_', ' ').title()} Pattern"
            )
            self.node_counters["analysis_pattern"] += 1
        
        # Link patterns to relevant domains
        pattern_domain_mapping = {
            "cost_benefit": ["economic"],
            "risk_based": ["legal", "environmental"],
            "market_failure": ["economic"],
            "stakeholder_analysis": ["social", "legal"],
            "impact_assessment": ["legal", "environmental", "social"],
            "baseline_comparison": ["economic", "environmental"],
            "subsidiarity_analysis": ["legal", "administrative"]
        }
        
        for pattern, domains in pattern_domain_mapping.items():
            pattern_node = f"pattern:{pattern}"
            if pattern_node in self.graph:
                for domain_type in domains:
                    domain_node = f"domain:{domain_type}"
                    if domain_node in self.graph:
                        self.graph.add_edge(
                            domain_node,
                            pattern_node,
                            relationship_type="uses_pattern",
                            weight=1.0
                        )
                        self.graph.add_edge(
                            pattern_node,
                            domain_node,
                            relationship_type="applies_to_domain",
                            weight=1.0
                        )
    
    def _process_chunk_file(self, chunk_file: Path):
        """Process a chunk file and add nodes/edges to graph."""
        with open(chunk_file, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        
        source_doc = chunks_data.get("source_document", "")
        chunks = chunks_data.get("chunks", [])
        
        # Create document node
        doc_node_id = f"document:{source_doc}"
        if doc_node_id not in self.graph:
            self.graph.add_node(
                doc_node_id,
                node_type="document",
                name=source_doc,
                label=source_doc,
                chunk_count=len(chunks)
            )
            self.node_counters["document"] += 1
        
        # Process each chunk
        for chunk in chunks:
            self._process_chunk(chunk, doc_node_id)
    
    def _process_chunk(self, chunk: Dict[str, Any], doc_node_id: str):
        """Process a single chunk and create nodes/edges."""
        chunk_id = chunk.get("chunk_id", "")
        chunk_type = chunk.get("chunk_type", "")
        metadata = chunk.get("metadata", {})
        
        # Create chunk node
        chunk_node_id = f"chunk:{chunk_id}"
        self.graph.add_node(
            chunk_node_id,
            node_type="chunk",
            chunk_type=chunk_type,
            chunk_id=chunk_id,
            name=chunk_id,
            label=f"{chunk_type.capitalize()} Chunk",
            content=chunk.get("content", "")[:500],  # Store first 500 chars
            metadata=metadata
        )
        self.node_counters["chunk"] += 1
        
        # Link chunk to document
        self.graph.add_edge(
            doc_node_id,
            chunk_node_id,
            relationship_type="contains_chunk",
            weight=1.0
        )
        self.graph.add_edge(
            chunk_node_id,
            doc_node_id,
            relationship_type="belongs_to_document",
            weight=1.0
        )
        
        # Process based on chunk type
        if chunk_type == "category":
            self._link_category_chunk(chunk_node_id, metadata)
        elif chunk_type == "analysis":
            self._link_analysis_chunk(chunk_node_id, metadata, chunk)
        elif chunk_type == "evidence":
            self._link_evidence_chunk(chunk_node_id, metadata, chunk)
    
    def _link_category_chunk(self, chunk_node_id: str, metadata: Dict[str, Any]):
        """Link category chunk to category node."""
        category = metadata.get("category")
        if category:
            category_node = f"category:{category}"
            if category_node in self.graph:
                self.graph.add_edge(
                    chunk_node_id,
                    category_node,
                    relationship_type="references_category",
                    weight=1.0
                )
                self.graph.add_edge(
                    category_node,
                    chunk_node_id,
                    relationship_type="has_chunk",
                    weight=1.0
                )
    
    def _link_analysis_chunk(self, chunk_node_id: str, metadata: Dict[str, Any], chunk: Dict[str, Any]):
        """Link analysis chunk to categories, domains, and patterns."""
        # Link to categories
        categories = metadata.get("categories", [])
        if not categories and metadata.get("category"):
            categories = [metadata["category"]]
        
        for category in categories:
            category_node = f"category:{category}"
            if category_node in self.graph:
                self.graph.add_edge(
                    chunk_node_id,
                    category_node,
                    relationship_type="analyzes_category",
                    weight=1.0
                )
                self.graph.add_edge(
                    category_node,
                    chunk_node_id,
                    relationship_type="has_analysis",
                    weight=1.0
                )
        
        # Link to domains (via categories)
        for category in categories:
            category_node = f"category:{category}"
            if category_node in self.graph:
                # Find domains connected to this category
                for domain_node in self.graph.successors(category_node):
                    if self.graph.nodes[domain_node].get("node_type") == "domain":
                        self.graph.add_edge(
                            chunk_node_id,
                            domain_node,
                            relationship_type="analyzes_domain",
                            weight=0.5
                        )
        
        # Link to analysis patterns
        analysis_type = metadata.get("analysis_type", "")
        patterns = self.ANALYSIS_TYPE_TO_PATTERNS.get(analysis_type, [])
        
        for pattern in patterns:
            pattern_node = f"pattern:{pattern}"
            if pattern_node in self.graph:
                self.graph.add_edge(
                    chunk_node_id,
                    pattern_node,
                    relationship_type="uses_pattern",
                    weight=1.0
                )
                self.graph.add_edge(
                    pattern_node,
                    chunk_node_id,
                    relationship_type="instantiated_by",
                    weight=1.0
                )
    
    def _link_evidence_chunk(self, chunk_node_id: str, metadata: Dict[str, Any], chunk: Dict[str, Any]):
        """Link evidence chunk to analysis chunks and categories."""
        # Link to document (already done)
        # Evidence chunks support analysis chunks
        
        # Find related analysis chunks in same document
        source_doc = chunk.get("source_document", "")
        if source_doc:
            # Get all chunks from same document
            doc_node = f"document:{source_doc}"
            if doc_node in self.graph:
                for chunk_node in self.graph.successors(doc_node):
                    if self.graph.nodes[chunk_node].get("chunk_type") == "analysis":
                        # Link evidence to analysis
                        self.graph.add_edge(
                            chunk_node_id,
                            chunk_node,
                            relationship_type="supports_analysis",
                            weight=1.0
                        )
                        self.graph.add_edge(
                            chunk_node,
                            chunk_node_id,
                            relationship_type="supported_by_evidence",
                            weight=1.0
                        )
        
        # Link to categories if present
        categories = metadata.get("categories", [])
        if not categories and metadata.get("category"):
            categories = [metadata["category"]]
        
        for category in categories:
            category_node = f"category:{category}"
            if category_node in self.graph:
                self.graph.add_edge(
                    chunk_node_id,
                    category_node,
                    relationship_type="evidence_for_category",
                    weight=0.5
                )
    
    def save_graph(self, output_path: str = "knowledge_graph.pkl"):
        """Save graph to pickle file."""
        output_file = Path(output_path)
        with open(output_file, 'wb') as f:
            pickle.dump(self.graph, f)
        print(f"💾 Graph saved to: {output_path}")
    
    def load_graph(self, input_path: str = "knowledge_graph.pkl") -> nx.MultiDiGraph:
        """Load graph from pickle file."""
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Graph file not found: {input_path}")
        
        with open(input_file, 'rb') as f:
            self.graph = pickle.load(f)
        
        print(f"📂 Graph loaded from: {input_path}")
        return self.graph
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        node_types = {}
        edge_types = {}
        
        for node, data in self.graph.nodes(data=True):
            node_type = data.get("node_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        for u, v, data in self.graph.edges(data=True):
            edge_type = data.get("relationship_type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types,
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }
    
    def query_related_chunks(self, chunk_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Query chunks related to a given chunk."""
        chunk_node = f"chunk:{chunk_id}"
        if chunk_node not in self.graph:
            return []
        
        related = []
        visited = set()
        
        # BFS to find related chunks
        queue = [(chunk_node, 0)]
        visited.add(chunk_node)
        
        while queue:
            current, depth = queue.pop(0)
            
            if depth > max_depth:
                continue
            
            # Get neighbors
            for neighbor in self.graph.successors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    node_data = self.graph.nodes[neighbor]
                    
                    if node_data.get("node_type") == "chunk":
                        related.append({
                            "chunk_id": node_data.get("chunk_id"),
                            "chunk_type": node_data.get("chunk_type"),
                            "depth": depth + 1,
                            "relationship": "related"
                        })
                        queue.append((neighbor, depth + 1))
        
        return related
    
    def get_chunks_by_category(self, category: str) -> List[str]:
        """Get all chunk IDs for a given category."""
        category_node = f"category:{category}"
        if category_node not in self.graph:
            return []
        
        chunk_ids = []
        for chunk_node in self.graph.successors(category_node):
            if self.graph.nodes[chunk_node].get("node_type") == "chunk":
                chunk_ids.append(self.graph.nodes[chunk_node].get("chunk_id"))
        
        return chunk_ids


def build_knowledge_graph(chunks_dir: str = "chunks", output_file: str = "knowledge_graph.pkl") -> nx.MultiDiGraph:
    """
    Build knowledge graph from chunks.
    
    Args:
        chunks_dir: Directory containing chunk JSON files
        output_file: Path to save graph pickle file
    
    Returns:
        NetworkX MultiDiGraph
    """
    builder = KnowledgeGraphBuilder()
    graph = builder.build_from_chunks(chunks_dir)
    
    # Save graph
    builder.save_graph(output_file)
    
    # Print statistics
    stats = builder.get_statistics()
    print("\n📊 Graph Statistics:")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print(f"\n   Node types:")
    for node_type, count in sorted(stats['node_types'].items()):
        print(f"     - {node_type}: {count}")
    print(f"\n   Edge types:")
    for edge_type, count in sorted(stats['edge_types'].items()):
        print(f"     - {edge_type}: {count}")
    
    return graph


if __name__ == "__main__":
    import sys
    
    chunks_dir = sys.argv[1] if len(sys.argv) > 1 else "chunks"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "knowledge_graph.pkl"
    
    try:
        graph = build_knowledge_graph(chunks_dir, output_file)
        print(f"\n✅ Knowledge graph built and saved!")
    except Exception as e:
        print(f"❌ Error building knowledge graph: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
