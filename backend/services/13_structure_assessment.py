"""Service: Structure the assessment into final format."""

from ..state.ria_state import RIAState
from ..impact_assessment_generator import ImpactAssessmentGenerator


# Global generator instance
_generator = None


def _get_generator() -> ImpactAssessmentGenerator:
    """Get or initialize ImpactAssessmentGenerator instance."""
    global _generator
    if _generator is None:
        _generator = ImpactAssessmentGenerator(enable_eurostat=True)
    return _generator


async def structure_assessment_node(state: RIAState) -> RIAState:
    """
    Structures the council output into final assessment format.
    
    Args:
        state: Current workflow state with 'stage3_result' and retrieval data
        
    Returns:
        Updated state with 'structured_assessment'
    """
    try:
        generator = _get_generator()
        stage3_result = state.get("stage3_result", {})
        
        # Build retrieved context for structuring
        retrieved_context = {
            "chunks": state.get("merged_chunks", []),
            "strategy": state.get("retrieval_strategy", "hybrid"),
            "metadata": {},
            "eurostat_data": state.get("eurostat_data", {})
        }
        
        # Use existing structure method
        structured = generator._structure_assessment(stage3_result, retrieved_context)
        
        state["structured_assessment"] = structured
        
        print(f"✅ Assessment structured: {len(structured.get('content', ''))} characters")
        
    except Exception as e:
        error_msg = f"Assessment structuring failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["structured_assessment"] = {}
    
    return state
