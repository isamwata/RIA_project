# Testing the LangGraph RIA Workflow

## Quick Start

### 1. Install Dependencies

```bash
# Option 1: Using pip
pip install langgraph typing-extensions

# Option 2: Using uv (if you have uv)
uv add langgraph typing-extensions

# Option 3: Using the setup script
chmod +x setup_and_test_langgraph.sh
./setup_and_test_langgraph.sh
```

### 2. Ensure Prerequisites

The workflow needs either:
- **Vector Store**: Run `python build_vector_store.py` to create it
- **Knowledge Graph**: Already exists at `knowledge_graph.pkl` ✅

You can run the workflow with just the knowledge graph - it will skip vector retrieval gracefully.

### 3. Run the Test

```bash
python test_langgraph_simple.py
```

Or use the original test:
```bash
python test_langgraph.py
```

## What the Test Does

The test will:

1. **Ingest** a sample AI regulation proposal
2. **Extract features** (categories, complexity)
3. **Route** to hybrid retrieval strategy
4. **Retrieve** from knowledge graph (and vector store if available)
5. **Synthesize** context from retrieved chunks
6. **Run LLM Council** (3 stages):
   - Stage 1: Generate initial opinions
   - Stage 2: Collect peer rankings
   - Stage 3: Meta-Chairman synthesis
7. **Extract** RIA sections from output
8. **Structure** final assessment
9. **Calculate** quality metrics
10. **Generate** final report

## Expected Output

You should see:
- Workflow progress through each node
- Retrieval results (chunk counts, scores)
- Council stage completions
- Quality metrics
- Final report summary
- JSON output saved to `test_langgraph_result.json`

## Troubleshooting

### LangGraph Import Error
```bash
pip install langgraph typing-extensions
```

### Vector Store Not Found
The workflow will still run using only the knowledge graph. To build the vector store:
```bash
python build_vector_store.py
```

### LLM API Errors
Ensure your `.env` file has:
```
OPENROUTER_API_KEY=your_key_here
```

### Network Issues
The workflow makes API calls to OpenRouter. Ensure you have network access.

## Sample Proposal

The test uses this proposal:
```
Regulation on Artificial Intelligence: Establishing a framework for 
trustworthy AI systems, including requirements for high-risk AI applications, 
transparency obligations, and governance mechanisms for AI development and 
deployment in the European Union.
```

You can modify `test_langgraph_simple.py` to test with your own proposals.
