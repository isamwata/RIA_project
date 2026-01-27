"""Service operations for RIA generation workflow."""

import importlib

# Import modules with numeric prefixes using importlib (Python doesn't allow dot notation for modules starting with numbers)
_01_ingest = importlib.import_module("backend.services.01_ingest_proposal")
_02_route = importlib.import_module("backend.services.02_route_retrieval")
_03_vector = importlib.import_module("backend.services.03_retrieve_vector_store")
_04_graph = importlib.import_module("backend.services.04_retrieve_knowledge_graph")
_05_eurostat = importlib.import_module("backend.services.05_fetch_eurostat_data")
_06_merge = importlib.import_module("backend.services.06_merge_context")
_07_euia = importlib.import_module("backend.services.07_fetch_euia_questions")
_08_synthesize = importlib.import_module("backend.services.08_synthesize_context")
_09_stage1 = importlib.import_module("backend.services.09_council_stage1")
_10_stage2 = importlib.import_module("backend.services.10_council_stage2")
_11_stage3 = importlib.import_module("backend.services.11_council_stage3")
_12_validate = importlib.import_module("backend.services.12_validate_output")
_13_structure = importlib.import_module("backend.services.13_structure_assessment")
_14_filter = importlib.import_module("backend.services.14_filter_forbidden_sections")
_15_extract = importlib.import_module("backend.services.15_extract_sections")

# Export the functions
ingest_proposal_node = _01_ingest.ingest_proposal_node
route_retrieval_node = _02_route.route_retrieval_node
route_retrieval_decision = _02_route.route_retrieval_decision
retrieve_vector_store_node = _03_vector.retrieve_vector_store_node
retrieve_knowledge_graph_node = _04_graph.retrieve_knowledge_graph_node
fetch_eurostat_data_node = _05_eurostat.fetch_eurostat_data_node
merge_context_node = _06_merge.merge_context_node
fetch_euia_questions_node = _07_euia.fetch_euia_questions_node
synthesize_context_node = _08_synthesize.synthesize_context_node
council_stage1_node = _09_stage1.council_stage1_node
council_stage2_node = _10_stage2.council_stage2_node
council_stage3_node = _11_stage3.council_stage3_node
validate_output_node = _12_validate.validate_output_node
validate_output_decision = _12_validate.validate_output_decision
structure_assessment_node = _13_structure.structure_assessment_node
filter_forbidden_sections_node = _14_filter.filter_forbidden_sections_node
extract_sections_node = _15_extract.extract_sections_node

__all__ = [
    "ingest_proposal_node",
    "route_retrieval_node",
    "route_retrieval_decision",
    "retrieve_vector_store_node",
    "retrieve_knowledge_graph_node",
    "fetch_eurostat_data_node",
    "merge_context_node",
    "fetch_euia_questions_node",
    "synthesize_context_node",
    "council_stage1_node",
    "council_stage2_node",
    "council_stage3_node",
    "validate_output_node",
    "validate_output_decision",
    "structure_assessment_node",
    "filter_forbidden_sections_node",
    "extract_sections_node",
]
