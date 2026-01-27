"""
Knowledge Graph Builder - Neo4j/AuraDB Implementation

Replaces NetworkX with Neo4j for graph operations.
Uses AuraDB connection for persistent graph storage.
"""

import os
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase


class KnowledgeGraphBuilder:
    """Builds and queries knowledge graph using Neo4j/AuraDB."""
    
    def __init__(self, uri: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (defaults to AuraDB from env vars)
            username: Neo4j username (defaults to env var)
            password: Neo4j password (defaults to env var)
        """
        # Get connection details from environment or parameters
        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        
        # Construct URI from instance ID if needed
        if not self.uri:
            instance_id = os.getenv("AURA_INSTANCEID")
            if instance_id:
                self.uri = f"neo4j+s://{instance_id}.databases.neo4j.io"
        
        if not self.uri or not self.password:
            raise ValueError("Neo4j connection details required. Set NEO4J_URI/NEO4J_PASSWORD or AURA_INSTANCEID")
        
        # Create driver (connection pool)
        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
        
        # Test connection
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def load_graph(self, input_path: Optional[str] = None) -> 'KnowledgeGraphBuilder':
        """
        Load graph from Neo4j (no-op for Neo4j, graph is already in database).
        Kept for compatibility with NetworkX interface.
        
        Args:
            input_path: Ignored (kept for compatibility)
        
        Returns:
            Self (for chaining)
        """
        # Graph is already in Neo4j, just verify connection
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"📂 Graph loaded from Neo4j: {count:,} nodes")
        return self
    
    def query_related_chunks(self, chunk_id: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """
        Query chunks related to a given chunk using graph traversal.
        
        Args:
            chunk_id: The chunk ID to find related chunks for
            max_depth: Maximum traversal depth
        
        Returns:
            List of related chunk dictionaries
        """
        chunk_node_id = f"chunk:{chunk_id}"
        
        # Cypher query for variable-depth traversal (max_depth must be literal, not parameter)
        # Build query with literal depth value
        query = f"""
        MATCH path = (start:Chunk {{id: $chunk_id}})-[*1..{max_depth}]-(related:Chunk)
        WHERE start.id = $chunk_id
        WITH related, length(path) as depth
        RETURN DISTINCT related.id as chunk_id, 
               related.chunk_type as chunk_type,
               related.chunk_id as chunk_id_prop,
               depth
        ORDER BY depth, related.id
        LIMIT 100
        """
        
        related = []
        try:
            with self.driver.session() as session:
                result = session.run(query, {"chunk_id": chunk_node_id})
                for record in result:
                    related.append({
                        "chunk_id": record.get("chunk_id_prop") or record.get("chunk_id", "").replace("chunk:", ""),
                        "chunk_type": record.get("chunk_type", ""),
                        "depth": record.get("depth", 1),
                        "relationship": "related"
                    })
        except Exception as e:
            print(f"⚠️  Error querying related chunks: {e}")
        
        return related
    
    def get_chunks_by_category(self, category: str) -> List[str]:
        """
        Get all chunk IDs for a given category.
        
        Args:
            category: Category name
        
        Returns:
            List of chunk IDs
        """
        category_node_id = f"category:{category}"
        
        query = """
        MATCH (cat:Category {id: $category_id})-[:HAS_CHUNK|REFERENCES_CATEGORY*]-(chunk:Chunk)
        RETURN DISTINCT chunk.chunk_id as chunk_id
        ORDER BY chunk_id
        """
        
        chunk_ids = []
        try:
            with self.driver.session() as session:
                result = session.run(query, {"category_id": category_node_id})
                for record in result:
                    chunk_id = record.get("chunk_id")
                    if chunk_id:
                        chunk_ids.append(chunk_id)
        except Exception as e:
            print(f"⚠️  Error querying chunks by category: {e}")
        
        return chunk_ids
    
    def get_chunks_by_category_with_data(self, category: str) -> List[Dict[str, Any]]:
        """
        Get chunks for a category with full metadata (used by impact_assessment_generator).
        
        Args:
            category: Category name
        
        Returns:
            List of chunk dictionaries with metadata
        """
        category_node_id = f"category:{category}"
        
        query = """
        MATCH (cat:Category {id: $category_id})-[:HAS_CHUNK|REFERENCES_CATEGORY*]-(chunk:Chunk)
        RETURN DISTINCT chunk.chunk_id as chunk_id,
               chunk.chunk_type as chunk_type,
               chunk.content as content,
               chunk.metadata as metadata
        ORDER BY chunk_id
        LIMIT 50
        """
        
        chunks = []
        try:
            with self.driver.session() as session:
                result = session.run(query, {"category_id": category_node_id})
                for record in result:
                    chunk_id = record.get("chunk_id")
                    if chunk_id:
                        # Parse metadata if it's a string
                        metadata = record.get("metadata")
                        if isinstance(metadata, str):
                            import json
                            try:
                                metadata = json.loads(metadata)
                            except:
                                metadata = {}
                        
                        chunks.append({
                            "chunk_id": chunk_id,
                            "chunk_type": record.get("chunk_type", ""),
                            "content": record.get("content", ""),
                            "metadata": metadata or {}
                        })
        except Exception as e:
            print(f"⚠️  Error querying chunks by category: {e}")
        
        return chunks
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        stats = {
            "total_nodes": 0,
            "total_edges": 0,
            "node_types": {},
            "edge_types": {},
            "is_connected": False
        }
        
        try:
            with self.driver.session() as session:
                # Total nodes
                result = session.run("MATCH (n) RETURN count(n) as count")
                stats["total_nodes"] = result.single()["count"]
                
                # Total edges
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                stats["total_edges"] = result.single()["count"]
                
                # Node types
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    label = record["label"] or "Unknown"
                    stats["node_types"][label] = record["count"]
                
                # Edge types
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    rel_type = record["type"] or "Unknown"
                    stats["edge_types"][rel_type] = record["count"]
                
                # Check connectivity (simplified - check if graph has any paths)
                result = session.run("""
                    MATCH path = (a)-[*1..2]-(b)
                    RETURN count(path) > 0 as connected
                    LIMIT 1
                """)
                stats["is_connected"] = result.single()["connected"] if result.peek() else False
                
        except Exception as e:
            print(f"⚠️  Error getting statistics: {e}")
        
        return stats
    
    # Compatibility methods (for NetworkX interface)
    def save_graph(self, output_path: Optional[str] = None):
        """No-op for Neo4j (graph is already persisted)."""
        print("💾 Graph is already persisted in Neo4j/AuraDB")
    
    # Make it behave like NetworkX graph for compatibility
    @property
    def graph(self):
        """Return self for compatibility with NetworkX interface."""
        return self
    
    def __contains__(self, node_id: str) -> bool:
        """Check if node exists (for compatibility)."""
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n {id: $id}) RETURN count(n) > 0 as exists", {"id": node_id})
                return result.single()["exists"]
        except:
            return False
    
    def successors(self, node_id: str):
        """Get successor nodes (for compatibility with NetworkX)."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n {id: $id})-[r]->(m)
                    RETURN m.id as id, m as data
                """, {"id": node_id})
                for record in result:
                    yield record["id"]
        except:
            return iter([])
    
    @property
    def nodes(self):
        """Return node accessor (for compatibility)."""
        return NodeAccessor(self.driver)
    
    # EU IA Nexus Methods
    def get_euia_key_questions_for_theme(self, theme_number: int) -> List[Dict[str, Any]]:
        """
        Get Tool #19 key questions for a Belgian theme via EU IA nexus.
        
        Args:
            theme_number: Belgian theme number (1-21)
        
        Returns:
            List of dicts with subcategory_name, key_questions, mapping_strength, relevance_score
        """
        query = """
        MATCH (t:Theme {theme_number: $theme_num})-[r:MAPPED_TO]->(sub:EUIASubcategory)
        RETURN sub.subcategory_name as subcategory_name,
               sub.key_questions as key_questions,
               r.mapping_strength as mapping_strength,
               r.relevance_score as relevance_score,
               sub.parent_category as category_type
        ORDER BY r.relevance_score DESC, r.mapping_strength
        """
        
        questions = []
        try:
            with self.driver.session() as session:
                result = session.run(query, {"theme_num": theme_number})
                for record in result:
                    questions.append({
                        "subcategory_name": record.get("subcategory_name", ""),
                        "key_questions": record.get("key_questions", []),
                        "mapping_strength": record.get("mapping_strength", ""),
                        "relevance_score": record.get("relevance_score", 0.0),
                        "category_type": record.get("category_type", "")
                    })
        except Exception as e:
            print(f"⚠️  Error querying EU IA key questions: {e}")
        
        return questions
    
    def get_euia_subcategories_for_themes(self, theme_numbers: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get EU IA subcategories and key questions for multiple themes.
        
        Args:
            theme_numbers: List of Belgian theme numbers
        
        Returns:
            Dict mapping theme_number -> list of subcategory info
        """
        query = """
        MATCH (t:Theme)-[r:MAPPED_TO]->(sub:EUIASubcategory)
        WHERE t.theme_number IN $theme_nums
        RETURN t.theme_number as theme_number,
               sub.subcategory_name as subcategory_name,
               sub.key_questions as key_questions,
               r.mapping_strength as mapping_strength,
               r.relevance_score as relevance_score,
               sub.parent_category as category_type
        ORDER BY t.theme_number, r.relevance_score DESC
        """
        
        result_dict = {theme_num: [] for theme_num in theme_numbers}
        
        try:
            with self.driver.session() as session:
                result = session.run(query, {"theme_nums": theme_numbers})
                for record in result:
                    theme_num = record.get("theme_number")
                    if theme_num in result_dict:
                        result_dict[theme_num].append({
                            "subcategory_name": record.get("subcategory_name", ""),
                            "key_questions": record.get("key_questions", []),
                            "mapping_strength": record.get("mapping_strength", ""),
                            "relevance_score": record.get("relevance_score", 0.0),
                            "category_type": record.get("category_type", "")
                        })
        except Exception as e:
            print(f"⚠️  Error querying EU IA subcategories: {e}")
        
        return result_dict
    
    def get_euia_methodology_guidance(self) -> Dict[str, Any]:
        """
        Get Tool #19 methodology guidance (3-step process).
        
        Returns:
            Dict with methodology steps and guidance
        """
        return {
            "methodology_name": "Tool #19: Identification/Screening of Impacts",
            "steps": [
                {
                    "step": 1,
                    "name": "IDENTIFY",
                    "description": "Identify all potential impacts (economic, social, environmental)",
                    "guidance": "Screen all 21 themes for potential impacts considering positive/negative, direct/indirect, intended/unintended, short/long-term effects"
                },
                {
                    "step": 2,
                    "name": "SELECT",
                    "description": "Select significant impacts using proportionate analysis",
                    "guidance": "Focus on impacts with greatest magnitude, relevance to policy objectives, and importance for stakeholders (especially SMEs, specific regions, or cumulative impacts)"
                },
                {
                    "step": 3,
                    "name": "ASSESS",
                    "description": "Assess selected impacts qualitatively and quantitatively",
                    "guidance": "Use Tool #19 key questions for each impact category. Assess both direct behavioral changes and indirect effects leading to ultimate policy goals"
                }
            ],
            "stakeholder_categories": [
                "Citizens", "Consumers", "Workers", 
                "Enterprises (by size: micro, small, medium, large)",
                "Public authorities (EU, national, sub-national)",
                "Third countries"
            ],
            "impact_chain": "Direct behavioral changes → Indirect effects → Ultimate policy goals"
        }


class NodeAccessor:
    """Compatibility layer for NetworkX node access."""
    
    def __init__(self, driver):
        self.driver = driver
        self._cache = {}
    
    def __getitem__(self, node_id: str) -> Dict[str, Any]:
        """Get node data by ID."""
        if node_id in self._cache:
            return self._cache[node_id]
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n {id: $id})
                    RETURN n
                """, {"id": node_id})
                record = result.single()
                if record:
                    node_data = dict(record["n"])
                    self._cache[node_id] = node_data
                    return node_data
        except:
            pass
        
        return {}


def build_knowledge_graph(chunks_dir: str = "chunks", output_file: Optional[str] = None) -> KnowledgeGraphBuilder:
    """
    Build knowledge graph from chunks (migrated to Neo4j).
    This function now just returns a connection to the existing Neo4j graph.
    
    Args:
        chunks_dir: Ignored (kept for compatibility)
        output_file: Ignored (kept for compatibility)
    
    Returns:
        KnowledgeGraphBuilder instance connected to Neo4j
    """
    builder = KnowledgeGraphBuilder()
    print("✅ Connected to Neo4j knowledge graph")
    return builder


if __name__ == "__main__":
    import sys
    
    # Test connection
    try:
        builder = KnowledgeGraphBuilder()
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
        builder.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
