"""Service: Council Stage 3 - Meta-Chairman synthesis."""

from ..state.ria_state import RIAState
from ..council import stage3_synthesize_final


async def council_stage3_node(state: RIAState) -> RIAState:
    """
    Runs Council Stage 3: Meta-Chairman synthesizes final response.
    
    Args:
        state: Current workflow state with all council stage results
        
    Returns:
        Updated state with 'stage3_result'
    """
    try:
        proposal = state["proposal"]
        context = state.get("synthesized_context", "")
        stage1_results = state.get("stage1_results", [])
        stage2_results = state.get("stage2_results", [])
        retry_count = state.get("retry_count", 0)
        
        if not stage1_results or not stage2_results:
            raise ValueError("Stage 1 and Stage 2 results are required for Stage 3")
        
        # Run stage 3
        stage3_result = await stage3_synthesize_final(
            proposal,
            stage1_results,
            stage2_results,
            context=context,
            retry_attempt=retry_count
        )
        
        state["stage3_result"] = stage3_result
        
        print(f"✅ Council Stage 3 complete: Final synthesis generated")
        
    except Exception as e:
        error_msg = f"Council Stage 3 failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["stage3_result"] = {}
    
    return state
