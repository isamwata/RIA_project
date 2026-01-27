"""Service: Ingest and validate proposal input."""

from typing import Dict, Any
from ..state.ria_state import RIAState


async def ingest_proposal_node(state: RIAState) -> RIAState:
    """
    Validates and ingests the proposal.
    
    Args:
        state: Current workflow state with 'proposal' and optional 'context'
        
    Returns:
        Updated state with validated proposal and extracted metadata
    """
    proposal = state.get("proposal", "")
    
    if not proposal or not proposal.strip():
        state.setdefault("errors", []).append("Proposal text is empty")
        return state
    
    # Extract basic metadata from context if provided
    context = state.get("context", {})
    
    # Set defaults
    state.setdefault("retrieval_strategy", context.get("retrieval_strategy", "hybrid"))
    state.setdefault("top_k", context.get("top_k", 20))
    state.setdefault("retry_count", 0)
    state.setdefault("errors", [])
    
    print(f"✅ Ingested proposal: {len(proposal)} characters")
    
    return state
