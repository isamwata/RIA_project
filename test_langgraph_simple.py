#!/usr/bin/env python3
"""
Simple test script for LangGraph RIA workflow.
Handles missing dependencies gracefully.
"""

import asyncio
import sys
from pathlib import Path

# Check for langgraph
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️  LangGraph not installed.")
    print("   Install with: pip install langgraph typing-extensions")
    print("   Or: uv add langgraph typing-extensions")
    sys.exit(1)

# Try to import the workflow
try:
    from backend.ria_langgraph import run_ria_workflow
except ImportError as e:
    print(f"❌ Error importing workflow: {e}")
    sys.exit(1)


async def main():
    """Test the LangGraph workflow with a sample proposal."""
    
    print("🧪 Testing LangGraph RIA Workflow")
    print("=" * 60)
    
    # Sample proposal - Belgian regulatory proposal
    proposal = """Belgian Royal Decree on Artificial Intelligence Governance: Establishing a national framework for trustworthy AI systems in Belgium, including requirements for high-risk AI applications in public services, transparency obligations for AI systems used by federal and regional authorities, and governance mechanisms for AI development and deployment in the Belgian market. The regulation aims to ensure that AI systems used in Belgium are safe, transparent, traceable, non-discriminatory, and environmentally friendly, while promoting innovation and competitiveness in the Belgian market and ensuring compliance with EU AI Act requirements."""
    
    context = {
        "jurisdiction": "Belgian",
        "category": "Digital",
        "year": "2024",
        "document_type": "Impact Assessment",
        "retrieval_strategy": "hybrid"  # Use hybrid to test both retrieval methods
    }
    
    print(f"\n📋 Proposal:")
    print(f"   {proposal[:150]}...")
    print(f"\n🔍 Context:")
    for key, value in context.items():
        print(f"   {key}: {value}")
    
    # Check prerequisites
    print(f"\n🔍 Checking prerequisites...")
    vector_store_exists = Path("vector_store").exists()
    knowledge_graph_exists = Path("knowledge_graph.pkl").exists()
    
    print(f"   Vector store: {'✅ Found' if vector_store_exists else '⚠️  Not found (will skip vector retrieval)'}")
    print(f"   Knowledge graph: {'✅ Found' if knowledge_graph_exists else '⚠️  Not found (will skip graph retrieval)'}")
    
    if not vector_store_exists and not knowledge_graph_exists:
        print("\n⚠️  Warning: Neither vector store nor knowledge graph found.")
        print("   The workflow will run but retrieval will be limited.")
        print("   To build them:")
        print("     python build_vector_store.py")
        print("     python build_knowledge_graph.py")
    
    try:
        # Run workflow
        print(f"\n🚀 Starting workflow...")
        print("   (This may take a few minutes depending on LLM API response times)")
        print()
        
        result = await run_ria_workflow(
            proposal=proposal,
            context=context,
            vector_store_path="vector_store",
            knowledge_graph_path="knowledge_graph.pkl"
        )
        
        # Display results
        print("\n" + "=" * 60)
        print("✅ Workflow Complete!")
        print("=" * 60)
        
        # Show workflow path taken
        print(f"\n🛤️  Workflow Path:")
        strategy = result.get("retrieval_strategy", "unknown")
        print(f"   Retrieval strategy: {strategy}")
        
        vector_results = result.get("vector_results", [])
        graph_results = result.get("graph_results", [])
        merged_chunks = result.get("merged_chunks", [])
        
        print(f"   Vector results: {len(vector_results)} chunks")
        print(f"   Graph results: {len(graph_results)} chunks")
        print(f"   Merged chunks: {len(merged_chunks)} chunks")
        
        # Show features extracted
        features = result.get("features", {})
        if features:
            print(f"\n🔍 Extracted Features:")
            print(f"   Categories: {features.get('categories', [])}")
            print(f"   Complexity: {features.get('complexity', 'unknown')}")
            print(f"   Word count: {features.get('word_count', 0)}")
        
        # Show final report summary
        if "final_report" in result:
            report = result["final_report"]
            metadata = report.get("metadata", {})
            
            print(f"\n📊 Final Report Summary:")
            print(f"   Model: {metadata.get('model', 'unknown')}")
            print(f"   Generated at: {metadata.get('generated_at', 'unknown')}")
            print(f"   Retrieval strategy: {metadata.get('retrieval_strategy', 'unknown')}")
            print(f"   Chunks used: {metadata.get('chunks_used', 0)}")
            
            sections = report.get("sections", {})
            sections_filled = len([s for s in sections.values() if s])
            print(f"   Sections filled: {sections_filled}/{len(sections)}")
            
            if sections_filled > 0:
                print(f"\n   Sections found:")
                for section_name, section_content in sections.items():
                    if section_content:
                        print(f"     ✅ {section_name}: {len(section_content)} chars")
            
            sources = report.get("sources", [])
            print(f"   Sources: {len(sources)}")
            
            if sources:
                print(f"\n📚 Sources Used:")
                for i, source in enumerate(sources[:5], 1):
                    print(f"   {i}. {source.get('document', 'Unknown')}")
                    print(f"      Jurisdiction: {source.get('jurisdiction', 'Unknown')}")
                    print(f"      Category: {source.get('category', 'Unknown')}")
        
        # Show quality metrics
        if "quality_metrics" in result:
            metrics = result["quality_metrics"]
            print(f"\n📈 Quality Metrics:")
            
            if "retrieval" in metrics:
                retrieval = metrics["retrieval"]
                print(f"   Retrieval:")
                print(f"     - Chunks: {retrieval.get('chunk_count', 0)}")
                print(f"     - Avg score: {retrieval.get('avg_score', 0):.3f}")
                print(f"     - Quality OK: {'✅' if retrieval.get('quality_ok') else '❌'}")
            
            if "context" in metrics:
                context_metrics = metrics["context"]
                print(f"   Context:")
                print(f"     - Length: {context_metrics.get('length', 0)} chars")
                print(f"     - Chunk count: {context_metrics.get('chunk_count', 0)}")
                print(f"     - Valid: {'✅' if context_metrics.get('is_valid') else '❌'}")
            
            if "council" in metrics:
                council = metrics["council"]
                print(f"   Council:")
                print(f"     - Content length: {council.get('content_length', 0)} chars")
                print(f"     - Valid: {'✅' if council.get('is_valid') else '❌'}")
                print(f"     - Model: {council.get('model', 'unknown')}")
            
            if "overall" in metrics:
                overall = metrics["overall"]
                print(f"   Overall:")
                print(f"     - Completeness: {overall.get('completeness', 0):.2%}")
                print(f"     - Sections filled: {overall.get('sections_filled', 0)}/{overall.get('total_sections', 0)}")
                print(f"     - Sources: {overall.get('sources_count', 0)}")
        
        # Show council stages
        stage1_results = result.get("stage1_results", [])
        stage2_results = result.get("stage2_results", [])
        stage3_result = result.get("stage3_result", {})
        
        if stage1_results or stage2_results or stage3_result:
            print(f"\n🤖 Council Stages:")
            print(f"   Stage 1: {len(stage1_results)} opinions generated")
            print(f"   Stage 2: {len(stage2_results)} rankings collected")
            if stage3_result:
                print(f"   Stage 3: ✅ Final synthesis complete")
                print(f"      Model: {stage3_result.get('model', 'unknown')}")
        
        # Show errors if any
        if "errors" in result and result["errors"]:
            print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"   - {error.get('message', 'Unknown error')}")
                print(f"     Time: {error.get('timestamp', 'unknown')}")
        else:
            print(f"\n✅ No errors encountered")
        
        # Show retry count
        retry_count = result.get("retry_count", 0)
        if retry_count > 0:
            print(f"\n🔄 Retries: {retry_count} expansion/retry cycles")
        
        # Save result to file
        output_file = "test_langgraph_result.json"
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Full result saved to: {output_file}")
        
        # Show sample content
        if "final_report" in result:
            report = result["final_report"]
            content = report.get("content", "")
            if content:
                print(f"\n📄 Sample Content (first 800 chars):")
                print("-" * 60)
                print(content[:800])
                if len(content) > 800:
                    print("...")
                print("-" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Troubleshooting:")
        print("   1. Ensure LangGraph is installed: pip install langgraph")
        print("   2. Check that vector_store or knowledge_graph.pkl exist")
        print("   3. Verify OpenRouter API key is set in .env file")
        print("   4. Check network connectivity for LLM API calls")


if __name__ == "__main__":
    asyncio.run(main())
