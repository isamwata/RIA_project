"""Service: Fetch EU IA Tool #19 key questions from Neo4j."""

from ..state.ria_state import RIAState
from ..knowledge_graph_neo4j import KnowledgeGraphBuilder


# Global knowledge graph instance (reuse from retrieve_knowledge_graph)
_knowledge_graph = None


def _get_knowledge_graph():
    """Get or initialize knowledge graph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        try:
            builder = KnowledgeGraphBuilder()
            _knowledge_graph = builder.load_graph()
        except Exception as e:
            print(f"⚠️  Could not connect to Neo4j: {e}")
            _knowledge_graph = None
    return _knowledge_graph


async def fetch_euia_questions_node(state: RIAState) -> RIAState:
    """
    Fetches EU IA Tool #19 key questions for all 21 themes.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with 'euia_questions' and 'euia_methodology'
    """
    try:
        knowledge_graph = _get_knowledge_graph()
        if not knowledge_graph:
            state["euia_questions"] = {}
            state["euia_methodology"] = {}
            return state
        
        # Fetch questions for all 21 themes
        all_theme_numbers = list(range(1, 22))
        euia_questions = knowledge_graph.get_euia_subcategories_for_themes(all_theme_numbers)
        euia_methodology = knowledge_graph.get_euia_methodology_guidance()
        
        state["euia_questions"] = euia_questions
        state["euia_methodology"] = euia_methodology
        
        themes_with_questions = len([t for t in euia_questions.values() if t])
        print(f"✅ Fetched EU IA questions for {themes_with_questions} themes")
        
    except Exception as e:
        error_msg = f"EU IA questions fetch failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["euia_questions"] = {}
        state["euia_methodology"] = {}
    
    return state
