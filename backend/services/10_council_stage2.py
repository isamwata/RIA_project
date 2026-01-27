"""Service: Council Stage 2 - Peer review and ranking."""

from ..state.ria_state import RIAState
from ..council import stage2_collect_rankings


async def council_stage2_node(state: RIAState) -> RIAState:
    """
    Runs Council Stage 2: Collect peer rankings of Stage 1 responses.
    
    Args:
        state: Current workflow state with 'proposal', 'synthesized_context', and 'stage1_results'
        
    Returns:
        Updated state with 'stage2_results'
    """
    try:
        proposal = state["proposal"]
        context = state.get("synthesized_context", "")
        stage1_results = state.get("stage1_results", [])
        
        if not stage1_results:
            raise ValueError("Stage 1 results are required for Stage 2")
        
        # Run stage 2
        stage2_results, label_to_model = await stage2_collect_rankings(
            proposal,
            stage1_results,
            context=context
        )
        
        state["stage2_results"] = stage2_results
        state.setdefault("quality_metrics", {})["label_to_model"] = label_to_model
        
        print(f"✅ Council Stage 2 complete: {len(stage2_results)} rankings")
        
    except Exception as e:
        error_msg = f"Council Stage 2 failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["stage2_results"] = []
    
    return state
