"""Service: Retrieve chunks from vector store."""

from ..state.ria_state import RIAState
from ..vector_store import VectorStore
from pathlib import Path


# Global vector store instance (initialized once)
_vector_store = None


def _get_vector_store() -> VectorStore:
    """Get or initialize vector store instance."""
    global _vector_store
    if _vector_store is None:
        vector_store_path = "vector_store"
        if Path(vector_store_path).exists():
            _vector_store = VectorStore(use_local_model=True)
            _vector_store.load(vector_store_path)
            print(f"✅ Vector store loaded from: {vector_store_path}")
        else:
            raise RuntimeError(f"Vector store not found at: {vector_store_path}")
    return _vector_store


async def retrieve_vector_store_node(state: RIAState) -> RIAState:
    """
    Retrieves relevant chunks from vector store.
    
    Args:
        state: Current workflow state with 'proposal' and 'retrieval_strategy'
        
    Returns:
        Updated state with 'vector_results'
    """
    try:
        vector_store = _get_vector_store()
        proposal = state["proposal"]
        strategy = state.get("retrieval_strategy", "hybrid")
        top_k = state.get("top_k", 20)
        context = state.get("context", {})
        
        # Build metadata filters from context
        filters = {}
        if context:
            if "jurisdiction" in context:
                filters["jurisdiction"] = context["jurisdiction"]
            if "category" in context:
                filters["categories"] = context["category"]
            if "year" in context:
                filters["year"] = context["year"]
            if "document_type" in context:
                filters["document_type"] = context["document_type"]
        
        # Perform retrieval based on strategy
        if strategy in ["dense", "hybrid"]:
            dense_weight = 1.0 if strategy == "dense" else 0.7
            sparse_weight = 0.0 if strategy == "dense" else 0.3
            
            results = vector_store.search(
                proposal,
                top_k=top_k,
                filter_metadata=filters if filters else None,
                use_hybrid=(strategy == "hybrid"),
                dense_weight=dense_weight,
                sparse_weight=sparse_weight
            )
            state["vector_results"] = results
        elif strategy == "sparse":
            results = vector_store.search(
                proposal,
                top_k=top_k,
                filter_metadata=filters if filters else None,
                use_hybrid=False,
                dense_weight=0.0,
                sparse_weight=1.0
            )
            state["vector_results"] = results
        else:
            state["vector_results"] = []
        
        print(f"✅ Retrieved {len(state['vector_results'])} chunks from vector store")
        
    except Exception as e:
        error_msg = f"Vector store retrieval failed: {str(e)}"
        print(f"❌ {error_msg}")
        state.setdefault("errors", []).append(error_msg)
        state["vector_results"] = []
    
    return state
