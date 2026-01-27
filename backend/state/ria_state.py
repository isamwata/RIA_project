"""State schema for RIA generation workflow using LangGraph."""

from typing import TypedDict, List, Dict, Any, Optional, NotRequired
from typing_extensions import NotRequired


class RIAState(TypedDict):
    """State schema for RIA generation workflow."""
    
    # Input
    proposal: str
    context: NotRequired[Dict[str, Any]]  # metadata: jurisdiction, category, year, etc.
    
    # Processing
    retrieval_strategy: NotRequired[str]  # "dense", "sparse", "hybrid", "graph-first"
    top_k: NotRequired[int]  # Number of chunks to retrieve
    
    # Retrieval results
    vector_results: NotRequired[List[Dict[str, Any]]]
    graph_results: NotRequired[List[Dict[str, Any]]]
    eurostat_data: NotRequired[Dict[str, Any]]
    euia_questions: NotRequired[Dict[int, List[Dict[str, Any]]]]
    euia_methodology: NotRequired[Dict[str, Any]]
    
    # Merged context
    merged_chunks: NotRequired[List[Dict[str, Any]]]
    synthesized_context: NotRequired[str]
    
    # Council results
    stage1_results: NotRequired[List[Dict[str, Any]]]
    stage2_results: NotRequired[List[Dict[str, Any]]]
    stage3_result: NotRequired[Dict[str, Any]]
    
    # Output
    structured_sections: NotRequired[Dict[str, str]]
    structured_assessment: NotRequired[Dict[str, Any]]
    final_report: NotRequired[Dict[str, Any]]
    
    # Quality and control
    quality_metrics: NotRequired[Dict[str, Any]]
    errors: NotRequired[List[str]]
    retry_count: NotRequired[int]
    validation_passed: NotRequired[bool]
    
    # Control flow
    next_action: NotRequired[str]  # for conditional routing
