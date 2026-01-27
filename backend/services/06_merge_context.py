"""Service: Merge retrieval results from all sources."""

from ..state.ria_state import RIAState


async def merge_context_node(state: RIAState) -> RIAState:
    """
    Merges retrieval results from vector store, knowledge graph, and other sources.
    
    Args:
        state: Current workflow state with retrieval results
        
    Returns:
        Updated state with 'merged_chunks'
    """
    vector_results = state.get("vector_results", [])
    graph_results = state.get("graph_results", [])
    
    # Merge chunks, removing duplicates based on content hash or ID
    merged = []
    seen_content = set()
    
    # Add vector results
    for chunk in vector_results:
        content_id = chunk.get("metadata", {}).get("chunk_id") or chunk.get("content", "")[:100]
        if content_id not in seen_content:
            merged.append(chunk)
            seen_content.add(content_id)
    
    # Add graph results
    for chunk in graph_results:
        content_id = chunk.get("metadata", {}).get("chunk_id") or chunk.get("content", "")[:100]
        if content_id not in seen_content:
            merged.append(chunk)
            seen_content.add(content_id)
    
    state["merged_chunks"] = merged
    
    print(f"✅ Merged {len(merged)} unique chunks from all sources")
    
    return state
