"""Service: Extract sections from final content."""

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


async def extract_sections_node(state: RIAState) -> RIAState:
    """
    Extracts structured sections from the final assessment content.
    
    Args:
        state: Current workflow state with 'structured_assessment'
        
    Returns:
        Updated state with 'structured_sections' and 'final_report'
    """
    try:
        generator = _get_generator()
        structured = state.get("structured_assessment", {})
        content = structured.get("content", "")
        
        if not content:
            state["structured_sections"] = {}
            state["final_report"] = structured
            return state
        
        # Use existing extraction method
        sections = generator._extract_sections(content)
        
        # Filter sections to remove forbidden content
        sections = generator._filter_forbidden_from_extracted_sections(sections)
        
        # Build final report
        final_report = {
            **structured,
            "sections": sections
        }
        
        state["structured_sections"] = sections
        state["final_report"] = final_report
        
        print(f"✅ Extracted {len(sections)} sections")
        
    except Exception as e:
        error_msg = f"Section extraction failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["structured_sections"] = {}
        state["final_report"] = state.get("structured_assessment", {})
    
    return state
