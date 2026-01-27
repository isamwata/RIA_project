"""
Vector Store - Stage 4

Hybrid retrieval layer combining:
- Dense embeddings (semantic similarity)
- Sparse vectors (BM25 for lexical/keyword precision)
- Metadata filtering
"""

import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, PermissionError, FileNotFoundError):
    pass

# Import API key from centralized module
try:
    from .api_keys import OPENAI_API_KEY
except ImportError:
    import os
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Lazy import for sentence_transformers to avoid Keras issues when using OpenAI
SENTENCE_TRANSFORMERS_AVAILABLE = None
_SentenceTransformer = None

def _get_sentence_transformer():
    """Lazy import of SentenceTransformer - only when needed."""
    global SENTENCE_TRANSFORMERS_AVAILABLE, _SentenceTransformer
    if SENTENCE_TRANSFORMERS_AVAILABLE is None:
        try:
            from sentence_transformers import SentenceTransformer
            _SentenceTransformer = SentenceTransformer
            SENTENCE_TRANSFORMERS_AVAILABLE = True
        except (ImportError, ValueError) as e:
            # Catch both ImportError and Keras ValueError
            SENTENCE_TRANSFORMERS_AVAILABLE = False
            _SentenceTransformer = None
    return _SentenceTransformer if SENTENCE_TRANSFORMERS_AVAILABLE else None


@dataclass
class VectorStoreEntry:
    """Entry in the vector store."""
    chunk_id: str
    content: str
    dense_vector: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None
    tokens: List[str] = None  # For BM25


class VectorStore:
    """Hybrid vector store with dense and sparse vectors."""
    
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        use_local_model: bool = False,
        local_model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize vector store.
        
        Args:
            embedding_model: OpenAI embedding model name (default: text-embedding-3-small)
            use_local_model: Use local SentenceTransformer instead of OpenAI (default: False, use OpenAI)
            local_model_name: Local model name for SentenceTransformer
        """
        self.entries: List[VectorStoreEntry] = []
        self.bm25_index: Optional[BM25Okapi] = None
        self.embedding_model_name = embedding_model
        self.use_local_model = use_local_model
        
        # Initialize embedding model
        if use_local_model:
            SentenceTransformer = _get_sentence_transformer()
            if SentenceTransformer:
                try:
                    print(f"📦 Loading local embedding model: {local_model_name}")
                    self.embedding_model = SentenceTransformer(local_model_name)
                    self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                except Exception as e:
                    print(f"⚠️  Failed to load local model: {e}")
                    print("   Falling back to OpenAI embeddings")
                    use_local_model = False
                    self.use_local_model = False
            else:
                # Fall back to OpenAI if sentence-transformers not available
                print("⚠️  sentence-transformers not available (Keras issue), using OpenAI")
                use_local_model = False
                self.use_local_model = False
        
        # Use OpenAI if not using local model
        if not use_local_model:
            if OPENAI_AVAILABLE:
                print(f"📦 Using OpenAI embedding model: {embedding_model}")
                # Initialize OpenAI client with API key from environment
                import os
                # Try multiple ways to get the API key
                api_key = None
                if OPENAI_API_KEY:
                    api_key = OPENAI_API_KEY
                elif not api_key:
                    api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    # Last resort: try loading .env again
                    try:
                        from dotenv import load_dotenv
                        load_dotenv()
                        api_key = os.getenv("OPENAI_API_KEY")
                    except:
                        pass
                
                if not api_key:
                    raise RuntimeError(
                        "OPENAI_API_KEY not found. Please set it in .env file or environment variable."
                    )
                self.embedding_model = OpenAI(api_key=api_key)
                # text-embedding-3-small has 1536 dimensions
                # text-embedding-ada-002 has 1536 dimensions
                self.embedding_dim = 1536
                self.use_local_model = False
            else:
                print("⚠️  OpenAI package not installed!")
                print("   Install with: pip install openai")
                raise RuntimeError(
                    "No embedding model available. Install:\n"
                    "  pip install openai\n"
                    "  (or: pip install sentence-transformers for local embeddings)"
                )
    
    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Add chunks to the vector store.
        
        Args:
            chunks: List of chunk dictionaries from Stage 2
        """
        print(f"📥 Adding {len(chunks)} chunks to vector store...")
        
        skipped = 0
        for i, chunk in enumerate(chunks):
            try:
                entry = self._create_entry(chunk)
                self.entries.append(entry)
                if (i + 1) % 100 == 0:
                    print(f"   Processed {i + 1}/{len(chunks)} chunks...")
            except Exception as e:
                skipped += 1
                chunk_id = chunk.get("chunk_id", "unknown")
                print(f"   ⚠️  Skipping chunk {chunk_id[:50]}... (error: {str(e)[:50]})")
                continue
        
        if skipped > 0:
            print(f"   ⚠️  Skipped {skipped} chunks due to errors")
        
        # Build BM25 index
        if BM25_AVAILABLE:
            print("🔍 Building BM25 sparse index...")
            tokenized_corpus = [entry.tokens for entry in self.entries if entry.tokens]
            if tokenized_corpus:
                self.bm25_index = BM25Okapi(tokenized_corpus)
        else:
            print("⚠️  BM25 not available. Install with: pip install rank-bm25")
            print("   Continuing with dense embeddings only...")
        
        print(f"✅ Added {len(self.entries)} entries to vector store")
    
    def _create_entry(self, chunk: Dict[str, Any]) -> VectorStoreEntry:
        """Create a vector store entry from a chunk."""
        chunk_id = chunk.get("chunk_id", "")
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})
        
        # Generate dense embedding
        dense_vector = self._generate_embedding(content)
        
        # Tokenize for BM25
        tokens = self._tokenize(content)
        
        return VectorStoreEntry(
            chunk_id=chunk_id,
            content=content,
            dense_vector=dense_vector,
            metadata=metadata,
            tokens=tokens
        )
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate dense embedding for text."""
        # Truncate text if too long (OpenAI embeddings have 8K token limit)
        # Rough estimate: 1 token ≈ 4 characters, so 8K tokens ≈ 32K chars
        # Use 30K chars to be safe
        MAX_CHARS = 30000
        
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]
            # Try to truncate at a sentence boundary if possible
            last_period = text.rfind('.')
            last_newline = text.rfind('\n')
            truncate_at = max(last_period, last_newline)
            if truncate_at > MAX_CHARS * 0.8:  # Only if we find a good break point
                text = text[:truncate_at + 1]
        
        if self.use_local_model and self.embedding_model:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding
        elif OPENAI_AVAILABLE:
            response = self.embedding_model.embeddings.create(
                model=self.embedding_model_name,
                input=text
            )
            return np.array(response.data[0].embedding)
        else:
            raise RuntimeError("No embedding model available")
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25."""
        # Simple tokenization (can be enhanced with proper NLP)
        import re
        # Convert to lowercase and split on non-word characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search the vector store.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Metadata filters (jurisdiction, category, year, document_type)
            use_hybrid: Use hybrid search (dense + sparse)
            dense_weight: Weight for dense embeddings (0-1)
            sparse_weight: Weight for sparse vectors (0-1)
        
        Returns:
            List of search results with scores
        """
        # Filter entries by metadata
        filtered_entries = self._filter_by_metadata(filter_metadata)
        
        if not filtered_entries:
            return []
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        query_tokens = self._tokenize(query)
        
        # Calculate scores
        scores = []
        
        for entry in filtered_entries:
            # Dense similarity (cosine similarity)
            dense_score = self._cosine_similarity(query_embedding, entry.dense_vector)
            
            # Sparse score (BM25)
            sparse_score = 0.0
            if self.bm25_index and entry.tokens:
                # Find entry index in original corpus
                entry_idx = self.entries.index(entry)
                if entry_idx < len(self.bm25_index.doc_freqs):
                    sparse_score = self.bm25_index.get_scores(query_tokens)[entry_idx]
                    # Normalize BM25 score (typically 0-20, normalize to 0-1)
                    sparse_score = min(sparse_score / 20.0, 1.0)
            
            # Hybrid score
            if use_hybrid:
                hybrid_score = (dense_weight * dense_score) + (sparse_weight * sparse_score)
            else:
                hybrid_score = dense_score
            
            scores.append({
                "chunk_id": entry.chunk_id,
                "content": entry.content,
                "metadata": entry.metadata,
                "score": hybrid_score,
                "dense_score": dense_score,
                "sparse_score": sparse_score
            })
        
        # Sort by score and return top_k
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]
    
    def _filter_by_metadata(self, filters: Optional[Dict[str, Any]]) -> List[VectorStoreEntry]:
        """Filter entries by metadata."""
        if not filters:
            return self.entries
        
        filtered = []
        for entry in self.entries:
            if not entry.metadata:
                continue
            
            match = True
            for key, value in filters.items():
                entry_value = entry.metadata.get(key)
                
                # Handle list values (e.g., categories)
                if isinstance(entry_value, list):
                    if value not in entry_value:
                        match = False
                        break
                elif entry_value != value:
                    match = False
                    break
            
            if match:
                filtered.append(entry)
        
        return filtered
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def save(self, output_dir: str = "vector_store"):
        """Save vector store to disk."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save entries (without numpy arrays for JSON)
        entries_data = []
        dense_vectors = []
        
        for entry in self.entries:
            entries_data.append({
                "chunk_id": entry.chunk_id,
                "content": entry.content,
                "metadata": entry.metadata,
                "tokens": entry.tokens
            })
            dense_vectors.append(entry.dense_vector)
        
        # Save metadata
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                "entry_count": len(entries_data),
                "embedding_dim": self.embedding_dim,
                "embedding_model": self.embedding_model_name,
                "use_local_model": self.use_local_model,
                "created_at": datetime.now().isoformat()
            }, f, indent=2)
        
        # Save entries
        entries_file = output_path / "entries.json"
        with open(entries_file, 'w', encoding='utf-8') as f:
            json.dump(entries_data, f, indent=2, ensure_ascii=False)
        
        # Save dense vectors as numpy array
        vectors_file = output_path / "dense_vectors.npy"
        if dense_vectors:
            vectors_array = np.array(dense_vectors)
            np.save(vectors_file, vectors_array)
        
        # Save BM25 index
        if self.bm25_index:
            bm25_file = output_path / "bm25_index.pkl"
            with open(bm25_file, 'wb') as f:
                pickle.dump(self.bm25_index, f)
        
        print(f"💾 Vector store saved to: {output_path}")
    
    def load(self, input_dir: str = "vector_store"):
        """Load vector store from disk."""
        input_path = Path(input_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Vector store directory not found: {input_dir}")
        
        # Load metadata
        metadata_file = input_path / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load entries
        entries_file = input_path / "entries.json"
        with open(entries_file, 'r', encoding='utf-8') as f:
            entries_data = json.load(f)
        
        # Load dense vectors
        vectors_file = input_path / "dense_vectors.npy"
        dense_vectors = np.load(vectors_file) if vectors_file.exists() else []
        
        # Reconstruct entries
        self.entries = []
        for i, entry_data in enumerate(entries_data):
            entry = VectorStoreEntry(
                chunk_id=entry_data["chunk_id"],
                content=entry_data["content"],
                dense_vector=dense_vectors[i] if len(dense_vectors) > i else None,
                metadata=entry_data.get("metadata", {}),
                tokens=entry_data.get("tokens", [])
            )
            self.entries.append(entry)
        
        # Load BM25 index
        bm25_file = input_path / "bm25_index.pkl"
        if bm25_file.exists():
            with open(bm25_file, 'rb') as f:
                self.bm25_index = pickle.load(f)
        
        print(f"📂 Vector store loaded from: {input_path}")
        print(f"   Entries: {len(self.entries)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        stats = {
            "total_entries": len(self.entries),
            "embedding_dim": self.embedding_dim,
            "embedding_model": self.embedding_model_name,
            "has_bm25": self.bm25_index is not None
        }
        
        # Metadata distribution
        metadata_dist = {}
        for entry in self.entries:
            if entry.metadata:
                for key, value in entry.metadata.items():
                    if key not in metadata_dist:
                        metadata_dist[key] = {}
                    if isinstance(value, list):
                        for v in value:
                            metadata_dist[key][v] = metadata_dist[key].get(v, 0) + 1
                    else:
                        metadata_dist[key][value] = metadata_dist[key].get(value, 0) + 1
        
        stats["metadata_distribution"] = metadata_dist
        
        return stats


def build_vector_store(chunks_dir: str = "chunks", output_dir: str = "vector_store") -> VectorStore:
    """
    Build vector store from chunk files.
    
    Args:
        chunks_dir: Directory containing chunk JSON files
        output_dir: Directory to save vector store
    
    Returns:
        VectorStore instance
    """
    chunks_path = Path(chunks_dir)
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")
    
    chunk_files = list(chunks_path.glob("*_chunks.json"))
    
    if not chunk_files:
        raise ValueError(f"No chunk files found in {chunks_dir}")
    
    print(f"📚 Building vector store from {len(chunk_files)} chunk file(s)...")
    
    # Initialize vector store
    store = VectorStore(use_local_model=True)
    
    # Load all chunks
    all_chunks = []
    for chunk_file in chunk_files:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
            all_chunks.extend(chunks_data.get("chunks", []))
    
    # Add chunks to vector store
    store.add_chunks(all_chunks)
    
    # Save vector store
    store.save(output_dir)
    
    # Print statistics
    stats = store.get_statistics()
    print("\n📊 Vector Store Statistics:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Embedding dimension: {stats['embedding_dim']}")
    print(f"   Embedding model: {stats['embedding_model']}")
    print(f"   BM25 index: {'Yes' if stats['has_bm25'] else 'No'}")
    
    if "metadata_distribution" in stats:
        print(f"\n   Metadata distribution:")
        for key, dist in stats["metadata_distribution"].items():
            if key in ["jurisdiction", "category", "document_type", "year"]:
                print(f"     {key}:")
                for value, count in sorted(dist.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"       - {value}: {count}")
    
    return store


if __name__ == "__main__":
    import sys
    
    chunks_dir = sys.argv[1] if len(sys.argv) > 1 else "chunks"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "vector_store"
    
    try:
        store = build_vector_store(chunks_dir, output_dir)
        print(f"\n✅ Vector store built and saved!")
    except Exception as e:
        print(f"❌ Error building vector store: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
