# LangGraph RIA Workflow

This document describes the LangGraph implementation for orchestrating RIA (Regulatory Impact Assessment) document generation.

## Overview

The LangGraph workflow orchestrates the complete process of generating an EU-style Impact Assessment from a regulatory proposal, using both vector store and knowledge graph for retrieval, and the LLM Council for generation.

## Installation

Install required dependencies:

```bash
pip install langgraph typing-extensions
```

Or update your project dependencies:

```bash
uv sync  # if using uv
# or
pip install -e .
```

## Architecture

### State Schema

The workflow uses a `RIAState` TypedDict that flows through all nodes:

- **Input**: `proposal`, `context`
- **Processing**: `features`, `retrieval_strategy`, retrieval results, synthesized context
- **Council**: `stage1_results`, `stage2_results`, `stage3_result`
- **Output**: `structured_sections`, `structured_assessment`, `final_report`
- **Control**: `quality_metrics`, `errors`, `retry_count`, `human_review_required`

### Node Flow

```
START
  ↓
ingest_proposal → extract_features → route_retrieval_strategy
  ↓
    ├─→ [vector_only] → retrieve_vector → merge_results
    ├─→ [graph_only] → retrieve_graph → merge_results
    ├─→ [hybrid] → retrieve_vector → retrieve_graph → merge_results
    └─→ [graph_first] → retrieve_graph → retrieve_vector → merge_results
  ↓
check_retrieval_quality
  ↓
    ├─→ [low quality] → expand_retrieval → (loop back)
    └─→ [high quality] → synthesize_context
  ↓
validate_context_quality
  ↓
    ├─→ [insufficient] → expand_retrieval → (loop back)
    └─→ [sufficient] → council_stage1
  ↓
council_stage2 → council_stage3 → validate_council_output
  ↓
    ├─→ [low quality] → council_stage1 → (loop back)
    └─→ [high quality] → extract_ria_sections
  ↓
structure_assessment → calculate_quality_metrics → route_to_human_review
  ↓
    ├─→ [needs review] → human_review_checkpoint
    │                       ↓
    │                   [approved] → generate_report
    │                   [rejected] → END
    │                   [revision] → council_stage1 → (loop back)
    └─→ [auto-approve] → generate_report
  ↓
prepare_knowledge_base_update → update_vector_store → update_knowledge_graph
  ↓
END
```

## Usage

### Basic Usage

```python
import asyncio
from backend.ria_langgraph import run_ria_workflow

async def main():
    proposal = "Your regulatory proposal text here..."
    
    context = {
        "jurisdiction": "EU",
        "category": "Digital",
        "year": "2024",
        "document_type": "Impact Assessment",
        "retrieval_strategy": "hybrid"  # Optional
    }
    
    result = await run_ria_workflow(
        proposal=proposal,
        context=context,
        vector_store_path="vector_store",
        knowledge_graph_path="knowledge_graph.pkl"
    )
    
    # Access final report
    final_report = result.get("final_report", {})
    print(f"Generated {len(final_report.get('sections', {}))} sections")

asyncio.run(main())
```

### Using the Test Script

```bash
python test_langgraph.py
```

This will run a complete workflow with a sample AI regulation proposal.

## Key Nodes

### 1. Retrieval Nodes

- **`retrieve_from_vector_store`**: Semantic/keyword search using embeddings and BM25
- **`retrieve_from_knowledge_graph`**: Graph traversal to find related chunks by category/domain
- **`merge_retrieval_results`**: Combines and deduplicates results from both sources

### 2. Council Nodes

- **`council_stage1_generate`**: Generates initial opinions from all council models (parallel)
- **`council_stage2_rankings`**: Collects peer rankings with bootstrap evaluation
- **`council_stage3_synthesize`**: Meta-Chairman synthesizes final assessment

### 3. Quality Control Nodes

- **`check_retrieval_quality`**: Validates retrieval results (chunk count, scores)
- **`validate_context_quality`**: Checks if synthesized context is sufficient
- **`validate_council_output`**: Validates council output completeness
- **`calculate_quality_metrics`**: Computes overall quality scores

### 4. Output Nodes

- **`extract_ria_sections`**: Parses council output into EU IA sections
- **`structure_assessment`**: Formats into final RIA structure with metadata
- **`generate_report_output`**: Creates final report (JSON, PDF, DOCX, HTML)

## Retrieval Strategies

The workflow supports four retrieval strategies:

1. **`vector_only`**: Use only vector store (semantic/keyword search)
2. **`graph_only`**: Use only knowledge graph (category-based traversal)
3. **`hybrid`**: Use both vector store and knowledge graph (recommended)
4. **`graph_first`**: Start with graph, then supplement with vector store

Strategy is automatically selected based on:
- Proposal complexity
- Category matches
- User preference (if specified in context)

## Error Handling

The workflow includes error handling at multiple levels:

- **Retrieval errors**: Logged and can trigger retry with expanded parameters
- **Council errors**: Logged and can trigger retry with different models
- **Quality failures**: Trigger expansion/retry loops
- **Critical errors**: Generate partial output with error documentation

## Human-in-the-Loop

The workflow supports human review checkpoints:

- **Automatic routing**: Low quality outputs automatically route to review
- **Review checkpoint**: Interrupts workflow for human approval/rejection/revision
- **Revision loop**: Can loop back to council stages with feedback

## Knowledge Base Updates

After successful generation:

- **Vector Store**: New proposal chunks are embedded and indexed
- **Knowledge Graph**: New nodes and relationships are created
- **Metadata**: Proposal metadata is stored for future retrieval

## Configuration

The workflow uses existing backend configuration:

- **Vector Store**: Configured via `VectorStore` class
- **Knowledge Graph**: Configured via `KnowledgeGraphBuilder` class
- **LLM Council**: Configured via `config.py` (models, bootstrap settings)

## State Persistence

The workflow state can be persisted at checkpoints for:

- **Recovery**: Resume from last successful state
- **Debugging**: Inspect intermediate states
- **Auditing**: Track workflow execution history

## Performance Considerations

- **Parallel Execution**: Vector and graph retrieval can run in parallel (hybrid mode)
- **Caching**: Consider caching retrieval results for similar proposals
- **Streaming**: Council stages can stream results as they complete
- **Batch Processing**: Multiple proposals can be processed in parallel

## Extending the Workflow

To add new nodes:

1. Define node function: `def my_node(state: RIAState) -> RIAState:`
2. Add to graph: `workflow.add_node("my_node", self.my_node)`
3. Add edges: `workflow.add_edge("previous_node", "my_node")`
4. Update state schema if needed

## Troubleshooting

### LangGraph not installed
```bash
pip install langgraph
```

### Vector store not found
Ensure you've built the vector store:
```bash
python build_vector_store.py
```

### Knowledge graph not found
Ensure you've built the knowledge graph:
```bash
python build_knowledge_graph.py
```

### Import errors
Check that all backend modules are importable:
```python
from backend.vector_store import VectorStore
from backend.knowledge_graph import KnowledgeGraphBuilder
from backend.council import stage1_collect_responses
```

## Next Steps

- Add streaming support for real-time progress updates
- Implement state persistence for recovery
- Add more sophisticated quality metrics
- Implement actual knowledge base updates (currently placeholders)
- Add report generation in multiple formats (PDF, DOCX, HTML)
