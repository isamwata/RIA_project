"""Service: Synthesize context for LLM consumption."""

from ..state.ria_state import RIAState
from ..impact_assessment_generator import ImpactAssessmentGenerator


# Global generator instance for context synthesis
_generator = None


def _get_generator() -> ImpactAssessmentGenerator:
    """Get or initialize ImpactAssessmentGenerator instance."""
    global _generator
    if _generator is None:
        _generator = ImpactAssessmentGenerator(enable_eurostat=True)
    return _generator


async def synthesize_context_node(state: RIAState) -> RIAState:
    """
    Synthesizes all retrieved context into a format suitable for LLM consumption.
    
    Args:
        state: Current workflow state with all retrieval results
        
    Returns:
        Updated state with 'synthesized_context'
    """
    try:
        generator = _get_generator()
        
        # Build retrieved_context dict similar to existing pattern
        retrieved_context = {
            "chunks": state.get("merged_chunks", []),
            "strategy": state.get("retrieval_strategy", "hybrid"),
            "metadata": {},
            "eurostat_data": state.get("eurostat_data", {}),
            "euia_questions": state.get("euia_questions", {}),
            "euia_methodology": state.get("euia_methodology", {})
        }
        
        # Use existing synthesis method
        synthesized = generator._synthesize_context(retrieved_context, state["proposal"])
        
        state["synthesized_context"] = synthesized
        
        print(f"✅ Synthesized context: {len(synthesized)} characters")
        
    except Exception as e:
        error_msg = f"Context synthesis failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["synthesized_context"] = ""
    
    return state
