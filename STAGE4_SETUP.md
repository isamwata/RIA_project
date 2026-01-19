# Stage 4: Vector Store - Setup Instructions

## Dependencies

Install required packages:

```bash
pip install sentence-transformers rank-bm25
```

### What Each Package Does

- **sentence-transformers**: Local embedding model (no API key needed)
  - Uses `all-MiniLM-L6-v2` model by default
  - Generates 384-dimensional embeddings
  - Runs entirely locally

- **rank-bm25**: BM25 sparse vector implementation
  - For keyword-based lexical search
  - Essential for legal/technical precision

## Alternative: OpenAI Embeddings

If you prefer OpenAI embeddings (requires API key):

```bash
pip install openai
```

Then set `OPENAI_API_KEY` environment variable and modify code to use OpenAI instead of local model.

## Usage

### Build Vector Store

```bash
python3 build_vector_store.py
```

This will:
1. Load all chunks from `chunks/` directory
2. Generate dense embeddings for each chunk
3. Build BM25 sparse index
4. Save to `vector_store/` directory

### Query Vector Store

```bash
python3 query_vector_store.py
```

This demonstrates:
- Semantic search (dense embeddings)
- Keyword search (BM25)
- Hybrid search (dense + sparse)
- Metadata filtering

## Features

✅ **Dense Embeddings**: Semantic similarity search
✅ **Sparse Vectors (BM25)**: Keyword-based precision
✅ **Hybrid Search**: Combines both approaches
✅ **Metadata Filtering**: Filter by jurisdiction, category, year, document type

## Output

Vector store is saved to `vector_store/` directory:
- `metadata.json`: Store configuration
- `entries.json`: Chunk metadata and content
- `dense_vectors.npy`: Dense embeddings (numpy array)
- `bm25_index.pkl`: BM25 sparse index
