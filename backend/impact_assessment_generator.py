"""
Impact Assessment Generator - Stage 6

Generates high-quality, policy-grade impact assessments using:
- RAG retrieval (vector store + knowledge graph)
- LLM Council (Meta-Chairman) for synthesis
- EU Impact Assessment reasoning style
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from .vector_store import VectorStore
    from .knowledge_graph import KnowledgeGraphBuilder
    from .council import stage1_generate_opinions, stage2_collect_rankings, stage3_synthesize_final
    from .config import CHAIRMAN_MODEL
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class ImpactAssessmentGenerator:
    """Generates EU-style impact assessments using RAG and LLM Council."""
    
    # EU Impact Assessment structure
    EU_IA_SECTIONS = [
        "1. Problem Definition",
        "2. Objectives",
        "3. Policy Options",
        "4. Baseline Scenario",
        "5. Impact Assessment",
        "6. Stakeholder Analysis",
        "7. Cost-Benefit Analysis",
        "8. Subsidiarity and Proportionality",
        "9. Monitoring and Evaluation"
    ]
    
    def __init__(
        self,
        vector_store_path: str = "vector_store",
        knowledge_graph_path: str = "knowledge_graph.pkl"
    ):
        """
        Initialize the generator.
        
        Args:
            vector_store_path: Path to vector store directory
            knowledge_graph_path: Path to knowledge graph pickle file
        """
        if not IMPORTS_AVAILABLE:
            raise RuntimeError(f"Required imports not available: {IMPORT_ERROR}")
        
        # Load vector store
        self.vector_store = VectorStore(use_local_model=True)
        try:
            self.vector_store.load(vector_store_path)
            print(f"✅ Vector store loaded from: {vector_store_path}")
        except FileNotFoundError:
            print(f"⚠️  Vector store not found: {vector_store_path}")
            self.vector_store = None
        
        # Load knowledge graph
        self.knowledge_graph = None
        if Path(knowledge_graph_path).exists():
            builder = KnowledgeGraphBuilder()
            try:
                self.knowledge_graph = builder.load_graph(knowledge_graph_path)
                print(f"✅ Knowledge graph loaded from: {knowledge_graph_path}")
            except Exception as e:
                print(f"⚠️  Could not load knowledge graph: {e}")
    
    def generate(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        use_council: bool = True,
        retrieval_strategy: str = "hybrid",
        top_k: int = 20
    ) -> Dict[str, Any]:
        """
        Generate an impact assessment.
        
        Args:
            query: User query describing the regulatory proposal
            context: Additional context (proposal details, jurisdiction, etc.)
            use_council: Use LLM Council for generation (True) or single model (False)
            retrieval_strategy: "dense", "sparse", "hybrid", or "graph-first"
            top_k: Number of chunks to retrieve
        
        Returns:
            Generated impact assessment with sections and metadata
        """
        print(f"\n🔍 Generating Impact Assessment for: {query}")
        print("=" * 60)
        
        # Step 1: Retrieve relevant context
        retrieved_context = self._retrieve_context(
            query,
            strategy=retrieval_strategy,
            top_k=top_k,
            context=context
        )
        
        # Step 2: Synthesize context
        synthesized_context = self._synthesize_context(retrieved_context, query)
        
        # Step 3: Generate impact assessment
        if use_council:
            assessment = self._generate_with_council(query, synthesized_context)
        else:
            assessment = self._generate_single_model(query, synthesized_context)
        
        # Step 4: Structure the output
        structured_assessment = self._structure_assessment(assessment, retrieved_context)
        
        return structured_assessment
    
    def _retrieve_context(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 20,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieve relevant context using vector store and/or knowledge graph."""
        retrieved = {
            "chunks": [],
            "strategy": strategy,
            "metadata": {}
        }
        
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
        
        # Vector store retrieval
        if self.vector_store:
            if strategy in ["dense", "hybrid"]:
                # Dense or hybrid search
                dense_weight = 1.0 if strategy == "dense" else 0.7
                sparse_weight = 0.0 if strategy == "dense" else 0.3
                
                results = self.vector_store.search(
                    query,
                    top_k=top_k,
                    filter_metadata=filters if filters else None,
                    use_hybrid=(strategy == "hybrid"),
                    dense_weight=dense_weight,
                    sparse_weight=sparse_weight
                )
                retrieved["chunks"].extend(results)
            
            elif strategy == "sparse":
                # Sparse only (BM25)
                results = self.vector_store.search(
                    query,
                    top_k=top_k,
                    filter_metadata=filters if filters else None,
                    use_hybrid=False,
                    dense_weight=0.0,
                    sparse_weight=1.0
                )
                retrieved["chunks"].extend(results)
        
        # Knowledge graph retrieval (graph-first or hybrid)
        if self.knowledge_graph and strategy in ["graph-first", "hybrid"]:
            graph_chunks = self._retrieve_from_graph(query, top_k=top_k // 2)
            retrieved["chunks"].extend(graph_chunks)
        
        # Deduplicate and rank
        retrieved["chunks"] = self._deduplicate_chunks(retrieved["chunks"])
        retrieved["chunks"] = sorted(
            retrieved["chunks"],
            key=lambda x: x.get("score", 0),
            reverse=True
        )[:top_k]
        
        print(f"📚 Retrieved {len(retrieved['chunks'])} relevant chunks")
        
        return retrieved
    
    def _retrieve_from_graph(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve chunks using knowledge graph traversal."""
        if not self.knowledge_graph:
            return []
        
        # Extract keywords from query for category matching
        query_lower = query.lower()
        categories = []
        
        category_keywords = {
            "Environment": ["environment", "climate", "biodiversity", "nature", "ecosystem"],
            "Health": ["health", "medical", "disease", "patient"],
            "Digital": ["digital", "data", "cyber", "ai", "algorithm"],
            "Competition": ["competition", "market", "antitrust"],
            "Employment": ["employment", "labour", "worker", "job"]
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in query_lower for kw in keywords):
                categories.append(category)
        
        # Find chunks in matching categories
        chunks = []
        for category in categories[:3]:  # Limit to 3 categories
            category_node = f"category:{category}"
            if category_node in self.knowledge_graph:
                # Get chunks connected to this category
                for chunk_node in self.knowledge_graph.successors(category_node):
                    if self.knowledge_graph.nodes[chunk_node].get("node_type") == "chunk":
                        chunk_data = self.knowledge_graph.nodes[chunk_node]
                        chunks.append({
                            "chunk_id": chunk_data.get("chunk_id", ""),
                            "content": chunk_data.get("content", ""),
                            "metadata": chunk_data.get("metadata", {}),
                            "score": 0.8,  # Graph-based relevance score
                            "source": "knowledge_graph"
                        })
        
        return chunks[:top_k]
    
    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks based on chunk_id."""
        seen = set()
        unique = []
        
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            if chunk_id and chunk_id not in seen:
                seen.add(chunk_id)
                unique.append(chunk)
        
        return unique
    
    def _synthesize_context(
        self,
        retrieved: Dict[str, Any],
        query: str
    ) -> str:
        """Synthesize retrieved context into coherent text."""
        chunks = retrieved.get("chunks", [])
        
        if not chunks:
            return "No relevant context found."
        
        # Group chunks by type
        category_chunks = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "category"]
        analysis_chunks = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "analysis"]
        evidence_chunks = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "evidence"]
        
        synthesized = f"Context for Impact Assessment: {query}\n\n"
        
        if category_chunks:
            synthesized += "Policy Categories:\n"
            for chunk in category_chunks[:5]:
                cat = chunk.get("metadata", {}).get("category", "N/A")
                synthesized += f"- {cat}\n"
            synthesized += "\n"
        
        if analysis_chunks:
            synthesized += "Relevant Analysis:\n"
            for i, chunk in enumerate(analysis_chunks[:10], 1):
                content = chunk.get("content", "")[:300]
                synthesized += f"{i}. {content}...\n\n"
        
        if evidence_chunks:
            synthesized += "\nSupporting Evidence:\n"
            for i, chunk in enumerate(evidence_chunks[:10], 1):
                content = chunk.get("content", "")[:200]
                synthesized += f"{i}. {content}...\n\n"
        
        return synthesized
    
    async def _generate_with_council(
        self,
        query: str,
        context: str
    ) -> Dict[str, Any]:
        """Generate impact assessment using LLM Council (Meta-Chairman)."""
        print("🤖 Using LLM Council (Meta-Chairman) for generation...")
        
        # Create enhanced query with context
        enhanced_query = f"""Generate a comprehensive EU Impact Assessment for the following regulatory proposal:

{query}

Relevant Context:
{context}

Please provide a structured impact assessment following EU Impact Assessment conventions."""
        
        # Stage 1: Generate first opinions
        print("   Stage 1: Generating first opinions...")
        stage1_results = await stage1_generate_opinions(enhanced_query)
        
        # Stage 2: Collect rankings (with bootstrap)
        print("   Stage 2: Collecting peer rankings (bootstrap evaluation)...")
        stage2_results, label_to_model = await stage2_collect_rankings(
            enhanced_query,
            stage1_results
        )
        
        # Stage 3: Meta-Chairman synthesis
        print("   Stage 3: Meta-Chairman synthesizing final assessment...")
        final_result = await stage3_synthesize_final(
            enhanced_query,
            stage1_results,
            stage2_results
        )
        
        return {
            "model": final_result.get("model", CHAIRMAN_MODEL),
            "content": final_result.get("response", ""),
            "stage1_results": stage1_results,
            "stage2_results": stage2_results
        }
    
    def _generate_single_model(
        self,
        query: str,
        context: str
    ) -> Dict[str, Any]:
        """Generate impact assessment using single model (fallback)."""
        print("🤖 Using single model for generation...")
        
        # This would use a single LLM call
        # For now, return a placeholder
        return {
            "model": CHAIRMAN_MODEL,
            "content": f"Impact Assessment for: {query}\n\n{context}\n\n[Single model generation not fully implemented - use use_council=True]"
        }
    
    def _structure_assessment(
        self,
        assessment: Dict[str, Any],
        retrieved: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Structure the assessment into EU IA format."""
        content = assessment.get("content", "")
        
        # Parse content into sections (simple heuristic)
        structured = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": assessment.get("model", "unknown"),
                "retrieval_strategy": retrieved.get("strategy", "unknown"),
                "chunks_used": len(retrieved.get("chunks", [])),
                "sections": []
            },
            "content": content,
            "sections": self._extract_sections(content),
            "sources": self._extract_sources(retrieved.get("chunks", []))
        }
        
        return structured
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract sections from generated content."""
        sections = {}
        
        for section_name in self.EU_IA_SECTIONS:
            # Look for section in content
            section_num = section_name.split(".")[0]
            pattern = f"{section_num}\\.|{section_name}"
            
            import re
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Extract section content (until next section or end)
                start = match.end()
                next_section = re.search(rf"{int(section_num) + 1}\\.", content[start:], re.IGNORECASE)
                end = start + next_section.start() if next_section else len(content)
                sections[section_name] = content[start:end].strip()
            else:
                sections[section_name] = ""
        
        return sections
    
    def _extract_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract source information from retrieved chunks."""
        sources = []
        seen = set()
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            source_doc = metadata.get("source_document", "")
            
            if source_doc and source_doc not in seen:
                seen.add(source_doc)
                sources.append({
                    "document": source_doc,
                    "jurisdiction": metadata.get("jurisdiction", "Unknown"),
                    "document_type": metadata.get("document_type", "Unknown"),
                    "year": metadata.get("year", "Unknown"),
                    "category": metadata.get("category", metadata.get("categories", []))
                })
        
        return sources


async def generate_impact_assessment(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    use_council: bool = True,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an impact assessment.
    
    Args:
        query: Description of the regulatory proposal
        context: Additional context (jurisdiction, category, year, etc.)
        use_council: Use LLM Council (True) or single model (False)
        output_file: Optional path to save output JSON
    
    Returns:
        Generated impact assessment
    """
    generator = ImpactAssessmentGenerator()
    assessment = await generator.generate(
        query=query,
        context=context,
        use_council=use_council
    )
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(assessment, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Assessment saved to: {output_file}")
    
    return assessment


if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python impact_assessment_generator.py <query> [output_file]")
        print("Example: python impact_assessment_generator.py 'Regulation on nature restoration' output.json")
        sys.exit(1)
    
    query = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    async def main():
        context = {
            "jurisdiction": "EU",
            "category": "Environment",
            "year": "2022"
        }
        
        assessment = await generate_impact_assessment(
            query=query,
            context=context,
            use_council=True,
            output_file=output_file
        )
        
        print("\n✅ Impact Assessment Generated!")
        print(f"   Model: {assessment['metadata']['model']}")
        print(f"   Sections: {len(assessment['sections'])}")
        print(f"   Sources: {len(assessment['sources'])}")
    
    asyncio.run(main())
