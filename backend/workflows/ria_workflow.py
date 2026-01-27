"""LangGraph workflow for RIA generation with service chaining."""

try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️  LangGraph not installed. Install with: pip install -U langgraph")

from typing import Dict, Any, Literal

from ..state.ria_state import RIAState
from ..services import (
    ingest_proposal_node,
    route_retrieval_node,
    route_retrieval_decision,
    retrieve_vector_store_node,
    retrieve_knowledge_graph_node,
    fetch_eurostat_data_node,
    merge_context_node,
    fetch_euia_questions_node,
    synthesize_context_node,
    council_stage1_node,
    council_stage2_node,
    council_stage3_node,
    validate_output_node,
    validate_output_decision,
    structure_assessment_node,
    filter_forbidden_sections_node,
    extract_sections_node,
)


def build_ria_workflow() -> StateGraph:
    """
    Builds the LangGraph workflow for RIA generation.
    
    Returns:
        Compiled StateGraph workflow
    """
    if not LANGGRAPH_AVAILABLE:
        raise RuntimeError("LangGraph is not installed. Install with: pip install -U langgraph")
    
    # Create workflow
    workflow = StateGraph(RIAState)
    
    # Add all nodes
    workflow.add_node("ingest_proposal", ingest_proposal_node)
    workflow.add_node("route_retrieval", route_retrieval_node)
    workflow.add_node("retrieve_vector_store", retrieve_vector_store_node)
    workflow.add_node("retrieve_knowledge_graph", retrieve_knowledge_graph_node)
    workflow.add_node("fetch_eurostat_data", fetch_eurostat_data_node)
    workflow.add_node("merge_context", merge_context_node)
    workflow.add_node("fetch_euia_questions", fetch_euia_questions_node)
    workflow.add_node("synthesize_context", synthesize_context_node)
    workflow.add_node("council_stage1", council_stage1_node)
    workflow.add_node("council_stage2", council_stage2_node)
    workflow.add_node("council_stage3", council_stage3_node)
    workflow.add_node("validate_output", validate_output_node)
    workflow.add_node("structure_assessment", structure_assessment_node)
    workflow.add_node("filter_forbidden_sections", filter_forbidden_sections_node)
    workflow.add_node("extract_sections", extract_sections_node)
    
    # Set entry point
    workflow.set_entry_point("ingest_proposal")
    
    # Linear flow: ingest → route
    workflow.add_edge("ingest_proposal", "route_retrieval")
    
    # Conditional routing from route_retrieval
    workflow.add_conditional_edges(
        "route_retrieval",
        route_retrieval_decision,
        {
            "vector_only": "retrieve_vector_store",
            "graph_only": "retrieve_knowledge_graph",
            "hybrid": "retrieve_vector_store",  # Start with vector, then graph
            "graph_first": "retrieve_knowledge_graph"
        }
    )
    
    # After vector retrieval in hybrid mode, also retrieve from graph
    def should_retrieve_graph(state: RIAState) -> Literal["yes", "no"]:
        strategy = state.get("retrieval_strategy", "hybrid")
        return "yes" if strategy == "hybrid" else "no"
    
    workflow.add_conditional_edges(
        "retrieve_vector_store",
        should_retrieve_graph,
        {
            "yes": "retrieve_knowledge_graph",
            "no": "fetch_eurostat_data"  # Skip graph, go to Eurostat
        }
    )
    
    # After graph retrieval, go to Eurostat (always fetch Eurostat)
    workflow.add_edge("retrieve_knowledge_graph", "fetch_eurostat_data")
    
    # After Eurostat, merge all context
    workflow.add_edge("fetch_eurostat_data", "merge_context")
    
    # After merge, fetch EU IA questions
    workflow.add_edge("merge_context", "fetch_euia_questions")
    
    # After EU IA questions, synthesize context
    workflow.add_edge("fetch_euia_questions", "synthesize_context")
    
    # Council stages (sequential)
    workflow.add_edge("synthesize_context", "council_stage1")
    workflow.add_edge("council_stage1", "council_stage2")
    workflow.add_edge("council_stage2", "council_stage3")
    
    # After council, validate output
    workflow.add_edge("council_stage3", "validate_output")
    
    # Conditional routing from validation
    workflow.add_conditional_edges(
        "validate_output",
        validate_output_decision,
        {
            "pass": "structure_assessment",
            "retry": "council_stage1",  # Retry from stage 1 (not stage 2)
            "error": "structure_assessment"  # Even on error, try to structure what we have
        }
    )
    
    # Final processing chain
    workflow.add_edge("structure_assessment", "filter_forbidden_sections")
    workflow.add_edge("filter_forbidden_sections", "extract_sections")
    workflow.add_edge("extract_sections", END)
    
    # Compile workflow
    return workflow.compile()


class RIAWorkflow:
    """Wrapper class for RIA LangGraph workflow."""
    
    def __init__(self):
        """Initialize the workflow."""
        self.graph = build_ria_workflow()
    
    async def invoke(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the workflow with initial state.
        
        Args:
            initial_state: Initial state dict with 'proposal' and optional 'context'
            
        Returns:
            Final state with 'final_report'
        """
        # Convert dict to RIAState (TypedDict accepts dict)
        result = await self.graph.ainvoke(initial_state)
        return result
    
    def stream(self, initial_state: Dict[str, Any]):
        """
        Stream workflow execution.
        
        Args:
            initial_state: Initial state dict
            
        Yields:
            State updates as workflow progresses
        """
        return self.graph.astream(initial_state)
