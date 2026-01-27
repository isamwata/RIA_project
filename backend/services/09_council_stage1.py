"""Service: Council Stage 1 - Collect individual LLM responses."""

from ..state.ria_state import RIAState
from ..council import stage1_collect_responses


async def council_stage1_node(state: RIAState) -> RIAState:
    """
    Runs Council Stage 1: Collect individual responses from all council models.
    
    Args:
        state: Current workflow state with 'proposal' and 'synthesized_context'
        
    Returns:
        Updated state with 'stage1_results'
    """
    try:
        proposal = state["proposal"]
        context = state.get("synthesized_context", "")
        
        # Run stage 1
        stage1_results = await stage1_collect_responses(
            proposal,
            context=context,
            specialized_roles=True
        )
        
        # Check if we got at least one response
        if not stage1_results or len(stage1_results) == 0:
            error_msg = (
                "Council Stage 1 failed: No responses received from any model. "
                "This usually indicates API errors (check API keys, network connectivity, or model availability). "
                "Please check the logs above for specific error messages."
            )
            print(f"❌ {error_msg}")
            state.setdefault("errors", []).append(error_msg)
            state["stage1_results"] = []
            return state
        
        state["stage1_results"] = stage1_results
        
        print(f"✅ Council Stage 1 complete: {len(stage1_results)} responses")
        
        # Warn if we got fewer responses than expected (but don't treat as error)
        from ..config import COUNCIL_MODELS
        expected_count = len(COUNCIL_MODELS)
        if len(stage1_results) < expected_count:
            warning = (
                f"⚠️  Warning: Only {len(stage1_results)}/{expected_count} models responded. "
                f"Proceeding with {len(stage1_results)} responses for ranking. "
                f"Some API calls may have failed. Check logs above for details."
            )
            print(warning)
            # Don't add to errors - this is just a warning, workflow can continue
            # The ranking will work with any number of responses >= 1
        
    except Exception as e:
        error_msg = f"Council Stage 1 failed: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        state.setdefault("errors", []).append(error_msg)
        state["stage1_results"] = []
    
    return state
