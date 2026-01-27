"""Service: Retrieve chunks from knowledge graph (Neo4j)."""

from ..state.ria_state import RIAState
from ..knowledge_graph_neo4j import KnowledgeGraphBuilder


# Global knowledge graph instance (initialized once)
_knowledge_graph = None


def _get_knowledge_graph():
    """Get or initialize knowledge graph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        try:
            builder = KnowledgeGraphBuilder()
            _knowledge_graph = builder.load_graph()
            print(f"✅ Knowledge graph connected to Neo4j/AuraDB")
        except Exception as e:
            print(f"⚠️  Could not connect to Neo4j knowledge graph: {e}")
            _knowledge_graph = None
    return _knowledge_graph


async def retrieve_knowledge_graph_node(state: RIAState) -> RIAState:
    """
    Retrieves relevant chunks from knowledge graph.
    
    Args:
        state: Current workflow state with 'proposal'
        
    Returns:
        Updated state with 'graph_results'
    """
    try:
        knowledge_graph = _get_knowledge_graph()
        if not knowledge_graph:
            state["graph_results"] = []
            return state
        
        proposal = state["proposal"]
        top_k = state.get("top_k", 20)
        
        # Use existing method from ImpactAssessmentGenerator pattern
        # This would need to be adapted from the existing _retrieve_from_graph method
        # For now, return empty results
        state["graph_results"] = []
        
        print(f"✅ Retrieved {len(state['graph_results'])} chunks from knowledge graph")
        
    except Exception as e:
        error_msg = f"Knowledge graph retrieval failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["graph_results"] = []
    
    return state
