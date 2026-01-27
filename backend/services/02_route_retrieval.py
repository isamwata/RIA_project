"""Service: Route retrieval strategy decision."""

from typing import Literal
from ..state.ria_state import RIAState


async def route_retrieval_node(state: RIAState) -> RIAState:
    """
    Determines the retrieval strategy based on proposal and context.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with retrieval_strategy set
    """
    # Strategy is already set in ingest_proposal, but we can refine it here
    strategy = state.get("retrieval_strategy", "hybrid")
    
    # Could add logic here to determine strategy based on proposal content
    # For now, just ensure it's set
    state["retrieval_strategy"] = strategy
    
    print(f"✅ Routing to retrieval strategy: {strategy}")
    
    return state


def route_retrieval_decision(state: RIAState) -> Literal["vector_only", "graph_only", "hybrid", "graph_first"]:
    """
    Conditional routing decision for retrieval strategy.
    
    Args:
        state: Current workflow state
        
    Returns:
        Route name based on retrieval strategy
    """
    strategy = state.get("retrieval_strategy", "hybrid")
    
    if strategy == "dense" or strategy == "sparse":
        return "vector_only"
    elif strategy == "graph-first":
        return "graph_first"
    elif strategy == "hybrid":
        return "hybrid"
    else:
        return "vector_only"  # Default
