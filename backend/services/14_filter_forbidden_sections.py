"""Service: Filter out forbidden sections from content."""

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


async def filter_forbidden_sections_node(state: RIAState) -> RIAState:
    """
    Removes forbidden sections from the structured assessment.
    
    Args:
        state: Current workflow state with 'structured_assessment'
        
    Returns:
        Updated state with filtered content
    """
    try:
        generator = _get_generator()
        structured = state.get("structured_assessment", {})
        content = structured.get("content", "")
        
        if not content:
            return state
        
        # Use existing filter method
        filtered_content = generator._remove_forbidden_sections(content)
        
        # Update structured assessment
        structured["content"] = filtered_content
        state["structured_assessment"] = structured
        
        print(f"✅ Filtered forbidden sections")
        
    except Exception as e:
        error_msg = f"Forbidden sections filtering failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
    
    return state
