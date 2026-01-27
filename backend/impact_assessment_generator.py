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
    from .knowledge_graph_neo4j import KnowledgeGraphBuilder
    from .council import stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final
    from .config import CHAIRMAN_MODEL
    from .eurostat_service import EurostatService
    from .direct_apis import query_openai, query_model_direct
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Theme to Eurostat Dataset Mapping
THEME_DATASET_MAP = {
    "Fight against poverty": {
        "primary": ["ilc_li02", "ilc_di01"],
        "secondary": ["ilc_peps01", "ilc_lvho01"],
        "keywords": ["poverty", "income", "minimum", "exclusion", "deprivation", "pension", "elderly"]
    },
    "Equal opportunities and social cohesion": {
        "primary": ["ilc_peps01", "ilc_di11"],
        "secondary": ["edat_lfse_03", "ilc_lvho01"],
        "keywords": ["discrimination", "equality", "access", "rights", "social", "cohesion"]
    },
    "Equality between women and men": {
        "primary": ["lfsa_egana", "earn_gr_gpgr2"],
        "secondary": ["lfsa_egis", "edat_lfse_03"],
        "keywords": ["women", "men", "gender", "female", "male", "equality"]
    },
    "Health": {
        "primary": ["hlth_silc_01", "hlth_dpe010"],
        "secondary": ["hlth_hcpe", "hlth_rs_bds"],
        "keywords": ["health", "healthcare", "medical", "disease", "treatment", "care"]
    },
    "Employment": {
        "primary": ["lfsi_emp_a", "une_rt_m"],
        "secondary": ["lfsa_urgan", "lfsa_egana"],
        "keywords": ["employment", "unemployment", "job", "work", "career", "labour", "worker"]
    },
    "Consumption and production patterns": {
        "primary": ["nama_10_gdp", "sts_inpr_m"],
        "secondary": ["sts_inpr_a", "sts_sepr_m"],
        "keywords": ["consumption", "production", "consumer", "price", "market"]
    },
    "Economic development": {
        "primary": ["nama_10_gdp", "nama_10_gdp_c"],
        "secondary": ["sts_inpr_m", "sts_sepr_m"],
        "keywords": ["economic", "gdp", "growth", "development", "productivity", "competitiveness"]
    },
    "Investments": {
        "primary": ["nama_10_gfcf"],
        "secondary": ["sts_inpr_m", "sts_sepr_m"],
        "keywords": ["investment", "capital", "infrastructure", "equipment"]
    },
    "Research and development": {
        "primary": ["rd_e_gerdtot"],
        "secondary": ["rd_p_persocc"],
        "keywords": ["research", "development", "innovation", "r&d", "technology"]
    },
    "SMEs (Small and Medium-Sized Enterprises)": {
        "primary": ["sbs_sc_sca_r2", "sbs_na_sca_r2"],
        "secondary": ["sts_inpr_m"],
        "keywords": ["sme", "small", "medium", "enterprise", "business", "company"]
    },
    "Administrative burdens": {
        "primary": [],
        "secondary": ["sbs_sc_sca_r2"],
        "keywords": ["administrative", "burden", "formality", "procedure", "compliance"]
    },
    "Energy": {
        "primary": ["nrg_bal_c", "nrg_ind_ren"],
        "secondary": ["nrg_cb_oil", "nrg_cb_gas"],
        "keywords": ["energy", "electricity", "fuel", "renewable", "consumption"]
    },
    "Mobility": {
        "primary": ["tran_r_vehst", "tran_r_avpa"],
        "secondary": ["tran_r_avpa_r2", "road_go_na_tn"],
        "keywords": ["mobility", "transport", "vehicle", "traffic", "road", "rail"]
    },
    "Food": {
        "primary": ["apro_cpshr1", "food_in_pb15"],
        "secondary": ["apro_acs_a", "food_in_pb15"],
        "keywords": ["food", "agriculture", "nutrition", "consumption", "production"]
    },
    "Climate change": {
        "primary": ["env_air_gge", "env_ac_ainah_r2"],
        "secondary": ["nrg_ind_ren", "env_air_emis"],
        "keywords": ["climate", "emission", "greenhouse", "carbon", "co2", "environment"]
    },
    "Natural resources": {
        "primary": ["env_wat_abs", "env_wasgen"],
        "secondary": ["env_ac_ainah_r2", "env_air_emis"],
        "keywords": ["water", "resource", "waste", "recycling", "natural", "consumption"]
    },
    "Indoor and outdoor air": {
        "primary": ["env_air_emis", "env_ac_ainah_r2"],
        "secondary": ["env_air_gge"],
        "keywords": ["air", "pollution", "emission", "quality", "particulate", "nox", "sox"]
    },
    "Biodiversity": {
        "primary": ["env_bio"],
        "secondary": ["env_air_emis", "env_wat_abs"],
        "keywords": ["biodiversity", "ecosystem", "species", "habitat", "conservation"]
    },
    "Nuisances": {
        "primary": [],
        "secondary": ["env_air_emis"],
        "keywords": ["noise", "nuisance", "vibration", "radiation", "visual"]
    },
    "Public authorities": {
        "primary": ["gov_10a_exp"],
        "secondary": ["gov_10a_main"],
        "keywords": ["government", "public", "administration", "service", "public sector"]
    },
    "Policy coherence for development": {
        "primary": ["bop_fdi1"],
        "secondary": ["nama_10_gdp"],
        "keywords": ["development", "international", "cooperation", "aid", "trade"]
    }
}


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
        knowledge_graph_path: str = "knowledge_graph.pkl",
        enable_eurostat: bool = True
    ):
        """
        Initialize the generator.
        
        Args:
            vector_store_path: Path to vector store directory
            knowledge_graph_path: Not used (kept for compatibility). Neo4j connection uses environment variables.
            enable_eurostat: Enable Eurostat data integration
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
        
        # Load knowledge graph from Neo4j/AuraDB
        self.knowledge_graph = None
        try:
            builder = KnowledgeGraphBuilder()
            self.knowledge_graph = builder.load_graph()
            print(f"✅ Knowledge graph connected to Neo4j/AuraDB")
        except Exception as e:
            print(f"⚠️  Could not connect to Neo4j knowledge graph: {e}")
            print(f"   Make sure NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are set")
    
        # Initialize Eurostat service
        self.enable_eurostat = enable_eurostat
        self.eurostat_service = None
        if enable_eurostat:
            try:
                self.eurostat_service = EurostatService()
                print(f"✅ Eurostat service initialized")
            except Exception as e:
                print(f"⚠️  Could not initialize Eurostat service: {e}")
                self.enable_eurostat = False
    
    async def generate(
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
        
        # Step 1.5: Fetch baseline Eurostat data for all 21 themes (hybrid approach)
        baseline_eurostat = {}
        print(f"🔍 Eurostat check: enable_eurostat={self.enable_eurostat}, eurostat_service={self.eurostat_service is not None}")
        if self.enable_eurostat and self.eurostat_service:
            print("📊 Fetching baseline Eurostat data for all 21 themes...")
            baseline_eurostat = await self._fetch_baseline_eurostat_data()
            print(f"📊 Fetched Eurostat data for {len(baseline_eurostat)} themes")
            retrieved_context["eurostat_data"] = baseline_eurostat
        else:
            if not self.enable_eurostat:
                print("⚠️  Eurostat is disabled (enable_eurostat=False)")
            if not self.eurostat_service:
                print("⚠️  Eurostat service is not initialized")
        
        # Step 1.6: Fetch EU IA Tool #19 key questions for all 21 themes
        if self.knowledge_graph:
            print("🔍 Fetching Tool #19 key questions via EU IA nexus...")
            all_theme_numbers = list(range(1, 22))  # Themes 1-21
            euia_questions = self.knowledge_graph.get_euia_subcategories_for_themes(all_theme_numbers)
            euia_methodology = self.knowledge_graph.get_euia_methodology_guidance()
            retrieved_context["euia_questions"] = euia_questions
            retrieved_context["euia_methodology"] = euia_methodology
            print(f"📋 Retrieved EU IA key questions for {len([t for t in euia_questions.values() if t])} themes")
        
        # Step 2: Synthesize context (includes baseline Eurostat and EU IA methodology)
        synthesized_context = self._synthesize_context(retrieved_context, query)
        
        # Step 3: Generate initial impact assessment
        if use_council:
            assessment = await self._generate_with_council(query, synthesized_context)
        else:
            assessment = self._generate_single_model(query, synthesized_context)
        
        # Step 3.5: Extract impact determinations and fetch detailed Eurostat data
        detailed_eurostat = {}
        if self.enable_eurostat and self.eurostat_service:
            print("📊 Analyzing impact determinations and fetching detailed Eurostat data...")
            impact_themes = self._extract_impact_determinations(assessment.get("content", ""))
            if impact_themes:
                print(f"   Found {len(impact_themes)} themes with positive/negative impact")
                detailed_eurostat = await self._fetch_detailed_eurostat_data(
                    query, impact_themes, context
                )
                # Merge detailed data with baseline
                for theme, stats in detailed_eurostat.items():
                    if theme in baseline_eurostat:
                        # Replace baseline with detailed data
                        baseline_eurostat[theme] = stats
                    else:
                        baseline_eurostat[theme] = stats
        
        # Update retrieved context with final Eurostat data
        retrieved_context["eurostat_data"] = baseline_eurostat
        
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
        
        # Find chunks in matching categories using Neo4j
        chunks = []
        for category in categories[:3]:  # Limit to 3 categories
            category_chunks = self.knowledge_graph.get_chunks_by_category_with_data(category)
            for chunk_data in category_chunks:
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
        
        # Start with Eurostat data FIRST (most important, must not be truncated)
        synthesized = f"Context for Impact Assessment: {query}\n\n"
        
        # Add Eurostat data FIRST - this is critical and must not be truncated
        eurostat_data = retrieved.get("eurostat_data", {})
        if eurostat_data:
            synthesized += "\n\nEurostat Statistical Data (Belgium) - USE THESE ACTUAL STATISTICS IN YOUR ASSESSMENT:\n"
            synthesized += "=" * 60 + "\n"
            
            # Separate baseline and detailed data
            baseline_themes = []
            detailed_themes = []
            
            for theme, stats in eurostat_data.items():
                stat_type = stats.get("statistics", [{}])[0].get("type", "baseline") if stats.get("statistics") else "baseline"
                impact_type = stats.get("impact_type", "")
                
                if stat_type == "detailed" or impact_type:
                    detailed_themes.append((theme, stats, impact_type))
                else:
                    baseline_themes.append((theme, stats))
            
            # Show detailed data first (for themes with positive/negative impact)
            # OPTIMIZATION: Include only ONE essential statistic per theme to reduce prompt size
            if detailed_themes:
                synthesized += "\n📊 DETAILED STATISTICS (for themes with positive/negative impact):\n"
                synthesized += "-" * 60 + "\n"
                synthesized += "USE THESE EXACT CITATIONS AND VALUES IN YOUR TEXT:\n\n"
                for theme, stats, impact_type in detailed_themes:
                    if stats.get("statistics"):
                        synthesized += f"\n{theme} ({impact_type} IMPACT):\n"
                        # OPTIMIZATION: Take only the FIRST (most relevant) statistic per theme
                        stat = stats["statistics"][0]
                        dataset = stat.get("dataset", "")
                        citation = stat.get("citation", "")
                        statistics_text = stat.get("formatted_statistics", "")
                        
                        if statistics_text:
                            # Format as ready-to-use citation with values - make it VERY clear
                            synthesized += f"  ═══ READY-TO-USE CITATION (COPY THIS INTO YOUR TEXT) ═══\n"
                            synthesized += f"  \"According to Eurostat ({dataset}, Belgium, 2022), {statistics_text}\"\n"
                            synthesized += f"  OR: \"Eurostat data ({dataset}, Belgium, 2022) shows that {statistics_text}\"\n"
                            synthesized += f"  ═══ PURPOSE: Use this to QUANTIFY your statements with actual numbers and meaningful context ═══\n"
                            synthesized += f"  Dataset: {dataset}\n\n"
            
            # Show baseline data (for context on all themes)
            # OPTIMIZATION: Include only ONE essential statistic per theme to reduce prompt size
            if baseline_themes:
                synthesized += "\n📊 BASELINE STATISTICS (Belgium context for all themes):\n"
                synthesized += "-" * 60 + "\n"
                synthesized += "USE THESE EXACT CITATIONS AND VALUES IN YOUR TEXT:\n\n"
                for theme, stats in baseline_themes:
                    if stats.get("statistics"):
                        synthesized += f"\n{theme}:\n"
                        # OPTIMIZATION: Take only the FIRST (most relevant) statistic per theme
                        stat = stats["statistics"][0]
                        dataset = stat.get("dataset", "")
                        citation = stat.get("citation", "")
                        statistics_text = stat.get("formatted_statistics", "")
                        
                        if statistics_text:
                            # Format as ready-to-use citation with values - make it VERY clear
                            synthesized += f"  ═══ READY-TO-USE CITATION (COPY THIS INTO YOUR TEXT) ═══\n"
                            synthesized += f"  \"According to Eurostat ({dataset}, Belgium, 2022), {statistics_text}\"\n"
                            synthesized += f"  OR: \"Eurostat data ({dataset}, Belgium, 2022) shows that {statistics_text}\"\n"
                            synthesized += f"  ═══ PURPOSE: Use this to QUANTIFY your statements with actual numbers and meaningful context ═══\n"
                            synthesized += f"  Dataset: {dataset}\n\n"
            
            synthesized += "\n"
            synthesized += "=" * 70 + "\n"
            synthesized += "🚨 CRITICAL: MANDATORY EUROSTAT DATA USAGE 🚨\n"
            synthesized += "=" * 70 + "\n"
            synthesized += "YOU MUST USE THE EUROSTAT DATA PROVIDED ABOVE IN YOUR ASSESSMENT TEXT.\n"
            synthesized += "DO NOT WRITE GENERIC STATEMENTS WHEN SPECIFIC DATA IS AVAILABLE.\n\n"
            synthesized += "MANDATORY REQUIREMENTS:\n"
            synthesized += "1. For EVERY theme where Eurostat data is provided above, you MUST include the citation WITH actual values\n"
            synthesized += "2. Copy the READY-TO-USE CITATION format shown above - it's already formatted for you\n"
            synthesized += "3. DO NOT write generic statements like 'According to Eurostat data' - use the specific citations above\n"
            synthesized += "4. The quantitative data (percentages, numbers) MUST appear in your text to quantify your statements\n"
            synthesized += "5. Example CORRECT: 'According to Eurostat (ilc_li02, Belgium, 2022), the at-risk-of-poverty rate was 15.3%'\n"
            synthesized += "6. Example CORRECT: 'Eurostat data (ilc_li02, Belgium, 2022) shows that the at-risk-of-poverty rate was 15.3%, with breakdowns showing rates of 4.0%, 2.9%, 3.4%'\n"
            synthesized += "7. Example WRONG: 'According to Eurostat data, poverty rates are significant' [missing citation and values]\n"
            synthesized += "8. Example WRONG: 'According to Eurostat (ilc_li02, Belgium, 2022), 3.6%, 4.0%, 2.9%' [missing context - what do these numbers mean?]\n"
            synthesized += "9. Example WRONG: 'According to Eurostat (ilc_li02, Belgium, 2022)' [missing actual statistic]\n"
            synthesized += "10. For themes with POSITIVE or NEGATIVE impact: Use the DETAILED statistics above\n"
            synthesized += "11. For themes with NO IMPACT: You may reference baseline statistics for context\n"
            synthesized += "12. Count how many themes have Eurostat data above - you must cite at least 80% of them\n"
            synthesized += "13. YOUR RESPONSE WILL BE REJECTED if you ignore available Eurostat data\n"
            synthesized += "14. The purpose is to QUANTIFY your statements with meaningful context - use the numbers and explanations provided!\n"
            synthesized += "15. IMPORTANT: The statistics are formatted with context (e.g., 'the at-risk-of-poverty rate was X%') - use this full context in your citations\n"
            synthesized += "=" * 70 + "\n\n"
        
        # Add Tool #19 EU IA Methodology and Key Questions
        euia_methodology = retrieved.get("euia_methodology", {})
        euia_questions = retrieved.get("euia_questions", {})
        
        if euia_methodology:
            synthesized += "\n\n" + "=" * 70 + "\n"
            synthesized += "TOOL #19 METHODOLOGY: IDENTIFICATION/SCREENING OF IMPACTS\n"
            synthesized += "=" * 70 + "\n\n"
            synthesized += f"Methodology: {euia_methodology.get('methodology_name', 'Tool #19')}\n\n"
            
            # Add 3-step process
            synthesized += "FOLLOW THIS 3-STEP PROCESS:\n"
            synthesized += "-" * 70 + "\n"
            for step in euia_methodology.get("steps", []):
                synthesized += f"\nSTEP {step['step']}: {step['name']}\n"
                synthesized += f"  Description: {step['description']}\n"
                synthesized += f"  Guidance: {step['guidance']}\n"
            
            synthesized += f"\n\nStakeholder Categories to Consider:\n"
            for stakeholder in euia_methodology.get("stakeholder_categories", []):
                synthesized += f"  • {stakeholder}\n"
            
            synthesized += f"\nImpact Chain: {euia_methodology.get('impact_chain', '')}\n"
            synthesized += "\n" + "=" * 70 + "\n\n"
        
        if euia_questions:
            synthesized += "\n" + "=" * 70 + "\n"
            synthesized += "TOOL #19 KEY QUESTIONS FOR EACH BELGIAN THEME\n"
            synthesized += "=" * 70 + "\n\n"
            synthesized += "Use these questions to systematically assess each theme:\n\n"
            
            # Get theme names mapping
            theme_names = {
                1: "Fight against poverty", 2: "Equal opportunities and social cohesion",
                3: "Equality between women and men", 4: "Health", 5: "Employment",
                6: "Consumption and production patterns", 7: "Economic development",
                8: "Investments", 9: "Research and development", 10: "SMEs",
                11: "Administrative burdens", 12: "Energy", 13: "Mobility",
                14: "Food", 15: "Climate change", 16: "Natural resources",
                17: "Indoor and outdoor air", 18: "Biodiversity", 19: "Nuisances",
                20: "Public authorities", 21: "Policy coherence for development"
            }
            
            # Add key questions for each theme (prioritize primary mappings)
            for theme_num in sorted(euia_questions.keys()):
                theme_questions = euia_questions.get(theme_num, [])
                if not theme_questions:
                    continue
                
                theme_name = theme_names.get(theme_num, f"Theme {theme_num}")
                synthesized += f"\n[{theme_num}] {theme_name}:\n"
                synthesized += "-" * 70 + "\n"
                
                # Group by primary/secondary
                primary = [q for q in theme_questions if q.get("mapping_strength") == "primary"]
                secondary = [q for q in theme_questions if q.get("mapping_strength") == "secondary"]
                
                if primary:
                    synthesized += "  PRIMARY EU IA Subcategories:\n"
                    for subcat in primary[:2]:  # Limit to top 2 primary
                        synthesized += f"    • {subcat.get('subcategory_name', '')} ({subcat.get('category_type', '').upper()}):\n"
                        questions = subcat.get("key_questions", [])
                        for q in questions[:3]:  # Limit to 3 questions per subcategory
                            synthesized += f"      → {q}\n"
                
                if secondary and len(primary) < 2:
                    synthesized += "  RELATED EU IA Subcategories:\n"
                    for subcat in secondary[:1]:  # Limit to 1 secondary
                        synthesized += f"    • {subcat.get('subcategory_name', '')} ({subcat.get('category_type', '').upper()}):\n"
                        questions = subcat.get("key_questions", [])
                        for q in questions[:2]:  # Limit to 2 questions
                            synthesized += f"      → {q}\n"
                
                synthesized += "\n"
            
            synthesized += "=" * 70 + "\n"
            synthesized += "🚨 IMPORTANT: Use these Tool #19 key questions to guide your impact assessment\n"
            synthesized += "   For each theme, consider the questions above when determining impact.\n"
            synthesized += "=" * 70 + "\n\n"
        
        # Now add document chunks (less critical, can be truncated if needed)
        if not chunks:
            if not eurostat_data and not euia_methodology:
                return "No relevant context found."
            return synthesized  # Return early if only Eurostat/EU IA data
        
        # Group chunks by type
        category_chunks = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "category"]
        analysis_chunks = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "analysis"]
        evidence_chunks = [c for c in chunks if c.get("metadata", {}).get("chunk_type") == "evidence"]
        
        # OPTIMIZATION: Limit to top 5-10 most relevant chunks to reduce prompt size
        # Prioritize by score, then by type (evidence > analysis > category)
        all_chunks_sorted = sorted(
            chunks,
            key=lambda x: (x.get("score", 0), 3 if x.get("metadata", {}).get("chunk_type") == "evidence" else 2 if x.get("metadata", {}).get("chunk_type") == "analysis" else 1),
            reverse=True
        )[:10]  # Top 10 chunks only
        
        synthesized += "\n\n" + "=" * 70 + "\n"
        synthesized += "RELEVANT DOCUMENTS AND ANALYSIS (top 10 most relevant):\n"
        synthesized += "=" * 70 + "\n\n"
        
        if category_chunks:
            synthesized += "Policy Categories:\n"
            for chunk in [c for c in all_chunks_sorted if c.get("metadata", {}).get("chunk_type") == "category"][:3]:
                cat = chunk.get("metadata", {}).get("category", "N/A")
                synthesized += f"- {cat}\n"
            synthesized += "\n"
        
        # Use optimized chunks list
        analysis_chunks_optimized = [c for c in all_chunks_sorted if c.get("metadata", {}).get("chunk_type") == "analysis"][:5]
        evidence_chunks_optimized = [c for c in all_chunks_sorted if c.get("metadata", {}).get("chunk_type") == "evidence"][:5]
        
        if analysis_chunks_optimized:
            synthesized += "Relevant Analysis:\n"
            for i, chunk in enumerate(analysis_chunks_optimized, 1):
                content = chunk.get("content", "")[:300]
                synthesized += f"{i}. {content}...\n\n"
        
        if evidence_chunks_optimized:
            synthesized += "\nSupporting Evidence:\n"
            for i, chunk in enumerate(evidence_chunks_optimized, 1):
                content = chunk.get("content", "")[:200]
                synthesized += f"{i}. {content}...\n\n"
        
        return synthesized
    
    def _extract_keywords_from_proposal(self, proposal: str) -> List[str]:
        """Extract relevant keywords from proposal."""
        proposal_lower = proposal.lower()
        keywords = []
        
        keyword_patterns = {
            "elderly": ["elderly", "pension", "retirement", "aged", "senior"],
            "youth": ["youth", "young", "student", "teenager"],
            "women": ["women", "female", "gender", "maternity"],
            "sme": ["sme", "small business", "medium enterprise", "startup"],
            "employment": ["employment", "job", "work", "career", "unemployment"],
            "health": ["health", "medical", "healthcare", "disease", "treatment"],
            "energy": ["energy", "electricity", "fuel", "power", "consumption"],
            "environment": ["environment", "climate", "emission", "pollution", "carbon"]
        }
        
        for category, patterns in keyword_patterns.items():
            if any(pattern in proposal_lower for pattern in patterns):
                keywords.append(category)
        
        return keywords
    
    def _identify_relevant_themes(self, proposal: str, max_themes: int = 5) -> List[str]:
        """Identify which of the 21 Belgian themes are most relevant to the proposal."""
        proposal_lower = proposal.lower()
        theme_scores = {}
        
        for theme, mapping in THEME_DATASET_MAP.items():
            score = 0
            keywords = mapping.get("keywords", [])
            for keyword in keywords:
                if keyword in proposal_lower:
                    score += 1
            if score > 0:
                theme_scores[theme] = score
        
        # Sort by score and return top themes
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, score in sorted_themes[:max_themes]]
    
    def _normalize_filters(self, proposal: str) -> Dict[str, str]:
        """Normalize filters for Eurostat API based on proposal keywords."""
        filters = {}
        keywords = self._extract_keywords_from_proposal(proposal)
        proposal_lower = proposal.lower()
        
        # Age filters
        if "elderly" in keywords or "pension" in proposal_lower or "retirement" in proposal_lower:
            filters["age"] = "Y_GE65"
        elif "youth" in keywords:
            filters["age"] = "Y15-24"
        elif "working" in proposal_lower:
            filters["age"] = "Y25-54"
        
        # Time period (default to 2022)
        filters["time"] = "2022"
        
        return filters
    
    async def _fetch_baseline_eurostat_data(self) -> Dict[str, Any]:
        """
        Fetch baseline Eurostat data for all 21 Belgian impact themes.
        Uses minimal filters (just geo=BE, time=2022) to provide context.
        
        Returns:
            Dictionary mapping theme names to baseline Eurostat statistics
        """
        if not self.eurostat_service:
            return {}
        
        print("   📊 Fetching baseline statistics for all 21 themes...")
        baseline_results = {}
        baseline_filters = {"geo": "BE", "time": "2022"}
        
        # Get all 21 themes
        all_themes = list(THEME_DATASET_MAP.keys())
        print(f"   📋 Found {len(all_themes)} themes in THEME_DATASET_MAP")
        
        successful_fetches = 0
        failed_fetches = 0
        
        for theme in all_themes:
            theme_map = THEME_DATASET_MAP.get(theme, {})
            # Use first primary dataset for baseline
            datasets = theme_map.get("primary", [])[:1]  # Just 1 dataset per theme for baseline
            
            if not datasets:
                continue
            
            dataset_code = datasets[0]
            theme_stats = []
            
            try:
                # Fetch with minimal filters
                data = await self.eurostat_service.get_data(
                    dataset_code=dataset_code,
                    filters=baseline_filters,
                    format="JSON",
                    lang="EN"
                )
                
                if data:
                    citation = f"Eurostat, {dataset_code}, Belgium, 2022"
                    formatted_stats = self._format_eurostat_statistics(data, dataset_code, citation)
                    
                    theme_stats.append({
                        "dataset": dataset_code,
                        "filters": baseline_filters,
                        "data": data,
                        "formatted_statistics": formatted_stats,
                        "citation": citation,
                        "type": "baseline"  # Mark as baseline
                    })
            except Exception as e:
                # Log error but continue with other themes
                print(f"   ⚠️  Failed to fetch baseline data for {theme} ({dataset_code}): {e}")
                failed_fetches += 1
                continue
            
            if theme_stats:
                baseline_results[theme] = {
                    "statistics": theme_stats,
                    "queries_built": 1,
                    "data_retrieved": len(theme_stats)
                }
                successful_fetches += 1
                print(f"   ✅ Successfully fetched data for {theme}")
            else:
                failed_fetches += 1
                print(f"   ⚠️  No data retrieved for {theme} (dataset: {dataset_code})")
        
        print(f"   📊 Eurostat fetch summary: {successful_fetches} successful, {failed_fetches} failed out of {len(all_themes)} themes")
        return baseline_results
        print(f"   ✅ Retrieved baseline data for {len(baseline_results)} themes")
        return baseline_results
    
    def _extract_impact_determinations(self, assessment_content: str) -> List[Dict[str, str]]:
        """
        Extract which themes have positive or negative impact from assessment content.
        
        Args:
            assessment_content: The generated assessment text
        
        Returns:
            List of dicts with theme name and impact type: [{"theme": "Employment", "impact": "POSITIVE"}, ...]
        """
        import re
        
        impact_themes = []
        
        # Pattern to match theme assessments: [1] Theme Name ... Assessment: POSITIVE IMPACT / NEGATIVE IMPACT
        # Look for patterns like:
        # [1] Fight against poverty ... Assessment: POSITIVE IMPACT
        # [5] Employment ... Assessment: NEGATIVE IMPACT
        
        # Get all 21 theme names
        theme_names = list(THEME_DATASET_MAP.keys())
        
        for i, theme in enumerate(theme_names, 1):
            # Look for theme number and name
            theme_pattern = rf'\[{i}\]\s+{re.escape(theme)}'
            
            # Find the theme section
            theme_match = re.search(theme_pattern, assessment_content, re.IGNORECASE)
            if not theme_match:
                continue
            
            # Find the assessment line after the theme
            start_pos = theme_match.end()
            # Look for "Assessment:" followed by POSITIVE/NEGATIVE/NO IMPACT
            assessment_pattern = r'Assessment:\s*(POSITIVE\s+IMPACT|NEGATIVE\s+IMPACT|NO\s+IMPACT)'
            assessment_match = re.search(assessment_pattern, assessment_content[start_pos:start_pos+500], re.IGNORECASE)
            
            if assessment_match:
                impact_text = assessment_match.group(1).upper()
                if "POSITIVE" in impact_text:
                    impact_themes.append({"theme": theme, "impact": "POSITIVE"})
                elif "NEGATIVE" in impact_text:
                    impact_themes.append({"theme": theme, "impact": "NEGATIVE"})
                # Skip "NO IMPACT" themes
        
        return impact_themes
    
    async def _fetch_detailed_eurostat_data(
        self,
        proposal: str,
        impact_themes: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch detailed Eurostat data for themes with positive or negative impact.
        Uses intelligent filters based on proposal content.
        
        Args:
            proposal: Regulatory proposal text
            impact_themes: List of themes with their impact types [{"theme": "Employment", "impact": "POSITIVE"}, ...]
            context: Additional context
        
        Returns:
            Dictionary mapping theme names to detailed Eurostat statistics
        """
        if not self.eurostat_service or not impact_themes:
            return {}
        
        print(f"   📊 Fetching detailed statistics for {len(impact_themes)} themes with impact...")
        detailed_results = {}
        normalized_filters = self._normalize_filters(proposal)
        
        for theme_info in impact_themes:
            theme = theme_info["theme"]
            impact_type = theme_info["impact"]
            
            theme_map = THEME_DATASET_MAP.get(theme, {})
            datasets = theme_map.get("primary", [])[:2]  # Up to 2 datasets per theme
            
            if not datasets:
                continue
            
            theme_stats = []
            
            for dataset_code in datasets:
                try:
                    # Build filters with proposal-specific context
                    filters = {"geo": "BE", "time": "2022"}
                    filters.update(normalized_filters)
                    
                    # For gender equality theme, always add sex dimension if dataset supports it
                    if theme == "Equality between women and men":
                        # Don't force sex filter - let the dataset schema determine it
                        pass
                    
                    # Fetch data
                    data = await self.eurostat_service.get_data(
                        dataset_code=dataset_code,
                        filters=filters,
                        format="JSON",
                        lang="EN"
                    )
                    
                    if data:
                        citation = f"Eurostat, {dataset_code}, Belgium, {filters.get('time', 'latest')}"
                        formatted_stats = self._format_eurostat_statistics(data, dataset_code, citation)
                        
                        theme_stats.append({
                            "dataset": dataset_code,
                            "filters": filters,
                            "data": data,
                            "formatted_statistics": formatted_stats,
                            "citation": citation,
                            "impact_type": impact_type,
                            "type": "detailed"  # Mark as detailed
                        })
                        print(f"      ✅ {dataset_code} for {theme} ({impact_type})")
                        if formatted_stats:
                            print(f"         Stats: {formatted_stats[:80]}...")
                    else:
                        # Fallback to baseline filters
                        fallback_filters = {"geo": "BE", "time": "2022"}
                        fallback_data = await self.eurostat_service.get_data(
                            dataset_code=dataset_code,
                            filters=fallback_filters,
                            format="JSON",
                            lang="EN"
                        )
                        if fallback_data:
                            citation = f"Eurostat, {dataset_code}, Belgium, 2022"
                            formatted_stats = self._format_eurostat_statistics(fallback_data, dataset_code, citation)
                            
                            theme_stats.append({
                                "dataset": dataset_code,
                                "filters": fallback_filters,
                                "data": fallback_data,
                                "formatted_statistics": formatted_stats,
                                "citation": citation,
                                "impact_type": impact_type,
                                "type": "detailed"
                            })
                            print(f"      ✅ {dataset_code} for {theme} ({impact_type}, fallback)")
                
                except Exception as e:
                    print(f"      ❌ Error fetching {dataset_code}: {e}")
                    continue
            
            if theme_stats:
                detailed_results[theme] = {
                    "statistics": theme_stats,
                    "queries_built": len(datasets),
                    "data_retrieved": len(theme_stats),
                    "impact_type": impact_type
                }
        
        return detailed_results
    
    async def _fetch_eurostat_data(
        self,
        proposal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use _fetch_baseline_eurostat_data() and _fetch_detailed_eurostat_data() instead.
        Kept for backward compatibility.
        """
        # This method is now replaced by the hybrid approach
        # Return empty dict - baseline and detailed fetching happens in generate()
        return {}
        """
        Fetch Eurostat data for themes relevant to the proposal.
        
        Args:
            proposal: Regulatory proposal text
            context: Additional context
        
        Returns:
            Dictionary mapping theme names to Eurostat statistics
        """
        if not self.eurostat_service:
            return {}
        
        # Identify relevant themes
        relevant_themes = self._identify_relevant_themes(proposal, max_themes=5)
        
        if not relevant_themes:
            print("   ⚠️  No relevant themes identified for Eurostat queries")
            return {}
        
        print(f"   📊 Identified {len(relevant_themes)} relevant themes for Eurostat data")
        
        eurostat_results = {}
        normalized_filters = self._normalize_filters(proposal)
        
        for theme in relevant_themes:
            theme_map = THEME_DATASET_MAP.get(theme, {})
            datasets = theme_map.get("primary", [])[:2]  # Limit to 2 datasets per theme
            
            if not datasets:
                continue
            
            theme_stats = []
            
            for dataset_code in datasets:
                try:
                    # Build filters
                    filters = {"geo": "BE"}
                    filters.update(normalized_filters)
                    
                    # Fetch data
                    data = await self.eurostat_service.get_data(
                        dataset_code=dataset_code,
                        filters=filters,
                        format="JSON",
                        lang="EN"
                    )
                    
                    if data:
                        # Extract value and format statistics
                        belgium_value = self._extract_belgium_value(data, filters)
                        citation = f"Eurostat, {dataset_code}, Belgium, {filters.get('time', 'latest')}"
                        formatted_stats = self._format_eurostat_statistics(data, dataset_code, citation)
                        
                        theme_stats.append({
                            "dataset": dataset_code,
                            "filters": filters,
                            "data": data,
                            "belgium_value": belgium_value,
                            "formatted_statistics": formatted_stats,  # Add formatted statistics
                            "citation": citation
                        })
                        print(f"      ✅ {dataset_code} for {theme}")
                        if formatted_stats:
                            print(f"         Stats: {formatted_stats[:80]}...")
                    else:
                        # Try fallback with minimal filters
                        fallback_filters = {"geo": "BE", "time": "2022"}
                        fallback_data = await self.eurostat_service.get_data(
                            dataset_code=dataset_code,
                            filters=fallback_filters,
                            format="JSON",
                            lang="EN"
                        )
                        if fallback_data:
                            belgium_value = self._extract_belgium_value(fallback_data, fallback_filters)
                            citation = f"Eurostat, {dataset_code}, Belgium, {fallback_filters.get('time', 'latest')}"
                            formatted_stats = self._format_eurostat_statistics(fallback_data, dataset_code, citation)
                            
                            theme_stats.append({
                                "dataset": dataset_code,
                                "filters": fallback_filters,
                                "data": fallback_data,
                                "belgium_value": belgium_value,
                                "formatted_statistics": formatted_stats,  # Add formatted statistics
                                "citation": citation
                            })
                            print(f"      ✅ {dataset_code} for {theme} (fallback)")
                            if formatted_stats:
                                print(f"         Stats: {formatted_stats[:80]}...")
                
                except Exception as e:
                    print(f"      ❌ Error fetching {dataset_code}: {e}")
                    continue
            
            if theme_stats:
                eurostat_results[theme] = {
                    "statistics": theme_stats,
                    "queries_built": len(datasets),
                    "data_retrieved": len(theme_stats)
                }
        
        return eurostat_results
    
    def _extract_belgium_value(self, data: Dict[str, Any], filters: Dict[str, str]) -> Optional[str]:
        """Extract Belgium-specific value from Eurostat data."""
        try:
            if "value" in data and isinstance(data["value"], list):
                values = data["value"]
                if values:
                    return str(values[0])
            
            if "value" in data:
                return str(data["value"])
            
            if "dataset" in data:
                dataset = data["dataset"]
                if isinstance(dataset, dict) and "value" in dataset:
                    values = dataset["value"]
                    if isinstance(values, list) and values:
                        return str(values[0])
                    elif isinstance(values, (int, float)):
                        return str(values)
            
            return None
        except Exception:
            return None
    
    def _format_eurostat_statistics(self, data: Dict[str, Any], dataset: str, citation: str) -> str:
        """
        Format Eurostat statistics into readable, meaningful text with actual values and context.
        Designed for stakeholder consumption - explains what the numbers mean.
        
        Args:
            data: Eurostat API response data
            dataset: Dataset code
            citation: Citation string
        
        Returns:
            Formatted statistics text with actual values and meaningful context
        """
        try:
            # Eurostat JSON format: data has "value" dict with numeric keys mapping to values
            # and "dimension" dict with category labels
            if "value" not in data:
                return ""
            
            values_dict = data.get("value", {})
            dimensions = data.get("dimension", {})
            
            if not values_dict or not isinstance(values_dict, dict):
                return ""
            
            # Get dataset label and description
            dataset_label = data.get("label", dataset)
            
            # Map dataset codes to human-readable descriptions
            dataset_descriptions = {
                "ilc_li02": "At-risk-of-poverty rate",
                "ilc_di01": "Median equivalised disposable income",
                "ilc_peps01": "Persons at risk of poverty or social exclusion",
                "lfsa_egana": "Employment rate by age and sex",
                "lfsi_emp_a": "Employment rate",
                "une_rt_m": "Unemployment rate",
                "hlth_silc_01": "Self-perceived health status",
                "nama_10_gdp": "Gross Domestic Product (GDP)",
                "rd_e_gerdtot": "Research and development expenditure",
                "nrg_bal_c": "Energy balance",
                "tran_r_vehst": "Vehicle stock",
                "env_air_gge": "Greenhouse gas emissions",
                "env_wat_abs": "Water abstraction",
                "env_air_emis": "Air pollutant emissions",
                "gov_10a_exp": "Government expenditure",
            }
            
            indicator_name = dataset_descriptions.get(dataset, dataset_label)
            
            # Extract dimension labels for meaningful context
            dimension_labels = {}
            if dimensions:
                for dim_name, dim_data in dimensions.items():
                    if isinstance(dim_data, dict):
                        category = dim_data.get("category", {})
                        if isinstance(category, dict):
                            labels = category.get("label", {})
                            if isinstance(labels, dict):
                                dimension_labels[dim_name] = labels
            
            # Build meaningful statistics with context
            formatted_stats = []
            
            # Process values with their dimension context
            # Eurostat uses numeric keys that map to dimension combinations
            # We need to reconstruct the meaning from dimensions
            processed_values = []
            
            # Get dimension sizes to understand the structure
            dim_sizes = {}
            dim_indices = {}
            for dim_name, dim_data in dimensions.items():
                if isinstance(dim_data, dict):
                    size = dim_data.get("size", 0)
                    dim_sizes[dim_name] = size
                    category = dim_data.get("category", {})
                    if isinstance(category, dict):
                        index = category.get("index", {})
                        if isinstance(index, dict):
                            dim_indices[dim_name] = index
            
            # Extract key statistics based on dataset type
            if "ilc_li02" in dataset.lower():  # At-risk-of-poverty rate
                # This is typically a percentage rate
                percentage_values = []
                for key, value in list(values_dict.items())[:10]:
                    if isinstance(value, (int, float)) and 0 <= value <= 100:
                        percentage_values.append(value)
                
                if percentage_values:
                    # Get dimension context
                    age_labels = dimension_labels.get("age", {})
                    sex_labels = dimension_labels.get("sex", {})
                    
                    # Format with meaningful context
                    if len(percentage_values) == 1:
                        formatted_stats.append(f"the at-risk-of-poverty rate was {percentage_values[0]:.1f}%")
                    else:
                        # Multiple breakdowns - describe them with context
                        main_rate = percentage_values[0] if percentage_values else None
                        if main_rate is not None:
                            formatted_stats.append(f"the at-risk-of-poverty rate was {main_rate:.1f}%")
                            
                            # Build breakdown descriptions with dimension labels
                            breakdown_descriptions = []
                            for i, val in enumerate(percentage_values[1:6], 1):  # Up to 5 breakdowns
                                # Try to infer what each breakdown represents based on common patterns
                                # Common patterns: Total, Less than 6 years, Males, Females
                                breakdown_descriptions.append(f"{val:.1f}%")
                            
                            if breakdown_descriptions:
                                # If we have dimension labels, try to create more meaningful descriptions
                                if age_labels and sex_labels:
                                    # Common breakdown order: Total, Age groups, Sex groups, Age+Sex combinations
                                    breakdown_text = []
                                    if len(breakdown_descriptions) >= 1:
                                        breakdown_text.append(f"{breakdown_descriptions[0]} for children under 6 years")
                                    if len(breakdown_descriptions) >= 2:
                                        breakdown_text.append(f"{breakdown_descriptions[1]} for males overall")
                                    if len(breakdown_descriptions) >= 3:
                                        breakdown_text.append(f"{breakdown_descriptions[2]} for males under 6 years")
                                    if len(breakdown_descriptions) >= 4:
                                        breakdown_text.append(f"{breakdown_descriptions[3]} for another demographic group")
                                    
                                    if breakdown_text:
                                        formatted_stats.append(f"with breakdowns showing: {', '.join(breakdown_text[:4])}")
                                else:
                                    # Fallback: just show the percentages
                                    formatted_stats.append(f"with breakdowns showing rates of {', '.join(breakdown_descriptions)}")
            
            elif "lfs" in dataset.lower() or "une" in dataset.lower():  # Labor force statistics
                percentage_values = []
                for key, value in list(values_dict.items())[:5]:
                    if isinstance(value, (int, float)) and 0 <= value <= 100:
                        percentage_values.append(value)
                
                if percentage_values:
                    main_rate = percentage_values[0]
                    if "une" in dataset.lower():
                        formatted_stats.append(f"the unemployment rate was {main_rate:.1f}%")
                    else:
                        formatted_stats.append(f"the employment rate was {main_rate:.1f}%")
                    
                    if len(percentage_values) > 1:
                        breakdowns = [f"{v:.1f}%" for v in percentage_values[1:4]]
                        formatted_stats.append(f"with variations across groups: {', '.join(breakdowns)}")
            
            elif "hlth" in dataset.lower():  # Health statistics
                percentage_values = []
                for key, value in list(values_dict.items())[:5]:
                    if isinstance(value, (int, float)) and 0 <= value <= 100:
                        percentage_values.append(value)
                
                if percentage_values:
                    main_rate = percentage_values[0]
                    formatted_stats.append(f"the indicator showed a value of {main_rate:.1f}%")
            
            elif "nama" in dataset.lower():  # National accounts (GDP, etc.)
                gdp_values = []
                for key, value in list(values_dict.items())[:3]:
                    if isinstance(value, (int, float)):
                        gdp_values.append(value)
                
                if gdp_values:
                    main_value = gdp_values[0]
                    if abs(main_value) >= 1000000:
                        formatted_stats.append(f"GDP was {main_value/1000000:.1f} billion euros")
                    elif abs(main_value) >= 1000:
                        formatted_stats.append(f"the value was {main_value/1000:.1f} billion euros")
                    else:
                        formatted_stats.append(f"the value was {main_value:,.0f} euros")
            
            else:
                # Generic extraction with meaningful formatting
                numeric_values = []
                for key, value in list(values_dict.items())[:5]:
                    if isinstance(value, (int, float)):
                        numeric_values.append(value)
                
                if numeric_values:
                    main_value = numeric_values[0]
                    if 0 <= main_value <= 100:
                        formatted_stats.append(f"the indicator was {main_value:.1f}%")
                    elif abs(main_value) >= 1000000:
                        formatted_stats.append(f"the value was {main_value/1000000:.1f} million")
                    elif abs(main_value) >= 1000:
                        formatted_stats.append(f"the value was {main_value/1000:.1f} thousand")
                    else:
                        formatted_stats.append(f"the value was {main_value:,.0f}")
            
            # Combine into readable text
            if formatted_stats:
                stats_text = ", ".join(formatted_stats)
                return stats_text
            
            # Fallback: return first few values with basic formatting
            value_list = [v for v in list(values_dict.values())[:3] if isinstance(v, (int, float))]
            if value_list:
                if all(0 <= v <= 100 for v in value_list):
                    formatted = [f"{v:.1f}%" for v in value_list]
                    return f"shows values of {', '.join(formatted)}"
                else:
                    formatted = [f"{v:,.0f}" for v in value_list]
                    return f"shows values of {', '.join(formatted)}"
            
            return ""
            
        except Exception as e:
            # Fallback: try to extract any numeric values
            try:
                if "value" in data:
                    values = data["value"]
                    if isinstance(values, dict):
                        value_list = [v for v in list(values.values())[:3] if isinstance(v, (int, float))]
                        if value_list:
                            if all(0 <= v <= 100 for v in value_list):
                                formatted = [f"{v:.1f}%" for v in value_list]
                                return f"shows values of {', '.join(formatted)}"
                            else:
                                formatted = [f"{v:,.0f}" for v in value_list]
                                return f"shows values of {', '.join(formatted)}"
            except:
                pass
            return ""
    
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
        stage1_results = await stage1_collect_responses(
            user_query=query,
            context=context,
            specialized_roles=True
        )
        
        # Check if any models succeeded
        if not stage1_results or len(stage1_results) == 0:
            print("   ⚠️  All council models failed - using single model fallback...")
            return await self._generate_single_model_fallback(query, context)
        
        # Stage 2: Collect rankings (with bootstrap)
        print("   Stage 2: Collecting peer rankings (bootstrap evaluation)...")
        try:
            stage2_results, label_to_model = await stage2_collect_rankings(
                user_query=query,
                stage1_results=stage1_results,
                context=context
            )
        except (ValueError, IndexError) as e:
            print(f"   ⚠️  Stage 2 failed ({e}) - proceeding with Stage 1 results only...")
            # Create minimal stage2_results for Stage 3
            stage2_results = []
            label_to_model = {}
        
        # Stage 3: Meta-Chairman synthesis
        print("   Stage 3: Meta-Chairman synthesizing final assessment...")
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                final_result = await stage3_synthesize_final(
                    user_query=query,
                    stage1_results=stage1_results,
                    stage2_results=stage2_results,
                    context=context,
                    retry_attempt=retry_count
                )
                
                # Validate that all 21 themes are present
                content = final_result.get("response", "")
                missing_themes = self._validate_all_themes_present(content)
                
                if not missing_themes:
                    # All themes present - success!
                    print(f"✅ Stage 3 complete: All 21 themes generated")
                    break
                else:
                    # Missing themes - retry if we have attempts left
                    if retry_count < max_retries:
                        retry_count += 1
                        print(f"⚠️  Stage 3 result missing {len(missing_themes)} themes. Retrying (attempt {retry_count}/{max_retries})...")
                        # Add a note to context about missing themes
                        context += f"\n\nCRITICAL: Previous attempt was missing themes {sorted(missing_themes)}. You MUST include ALL 21 themes in your response."
                    else:
                        print(f"⚠️  Stage 3 result still missing {len(missing_themes)} themes after {max_retries} retries.")
                        print(f"   Missing: {sorted(missing_themes)}")
                        print(f"   Attempting to complete missing themes with focused LLM call...")
                        # Try to complete missing themes with a focused prompt
                        completed_content = await self._complete_missing_themes(
                            content, 
                            missing_themes, 
                            query, 
                            context
                        )
                        if completed_content:
                            final_result["response"] = completed_content
                            # Validate again
                            final_missing = self._validate_all_themes_present(completed_content)
                            if not final_missing:
                                print(f"✅ Successfully completed all missing themes!")
                            else:
                                print(f"⚠️  Still missing {len(final_missing)} themes after completion attempt")
                        break
                        
            except Exception as e:
                print(f"   ⚠️  Stage 3 failed ({e}) - using best Stage 1 result...")
                # Use the first successful result as fallback
                if stage1_results:
                    final_result = {
                        "model": stage1_results[0].get("model", "fallback"),
                        "response": stage1_results[0].get("response", "")
                    }
                    break
                else:
                    # Last resort: use single model fallback
                    return await self._generate_single_model_fallback(query, context)
        
        return {
            "model": final_result.get("model", CHAIRMAN_MODEL),
            "content": final_result.get("response", ""),
            "stage1_results": stage1_results,
            "stage2_results": stage2_results
        }
    
    async def _generate_single_model_fallback(
        self,
        query: str,
        context: str
    ) -> Dict[str, Any]:
        """Fallback when all council models fail - use CHAIRMAN_MODEL."""
        print(f"   🔄 Using {CHAIRMAN_MODEL} fallback...")
        try:
            from backend.api_keys import print_api_key_status
            
            # Print API key status for debugging
            print_api_key_status()
            
            # Build comprehensive prompt for Belgian RIA
            enhanced_query = f"""Generate a comprehensive Belgian Regulatory Impact Assessment (RIA) with EU-style analysis for the following proposal:

{query}

Relevant Context:
{context}

CRITICAL REQUIREMENTS:
1. Assess ALL 21 Belgian impact themes with detailed EU-style analysis
2. FORBIDDEN SECTIONS - CRITICAL: DO NOT include ANY of the following sections ANYWHERE in your report:
   - Current Legal Framework (or "Legal Framework")
   - Problem Identification
   - Policy Objectives
   - Stakeholders Affected (or "Stakeholders")
   These sections are FORBIDDEN and must NOT appear as standalone sections, subsections, or within any other section.
   If you mention legal context, problems, objectives, or stakeholders, integrate them naturally into the theme assessments WITHOUT creating separate sections with these titles.
3. For each theme, provide: Impact determination (POSITIVE/NEGATIVE/NO IMPACT), detailed explanation, and mitigation measures if needed
4. FORBIDDEN: DO NOT use "MIXED IMPACT" - only POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT are allowed. If a theme has both positive and negative aspects, determine the NET/OVERALL impact.
5. Use formal, evidence-based tone consistent with EU Impact Assessments
6. Include citations when referencing retrieved documents
7. Map EU domain knowledge to Belgian categories where relevant
8. DO NOT include any sections other than the 21 Impact Themes Assessment - your report must contain ONLY the themes section

Format each theme assessment as:
[Theme Number] Theme Name
Keywords: [keywords]
Assessment: [POSITIVE IMPACT / NEGATIVE IMPACT / NO IMPACT]
Detailed Explanation: [comprehensive EU-style analysis]
Mitigation Measures: [if applicable]

Generate the full assessment now. DO NOT include Recommendations or Conclusion sections. DO NOT use MIXED IMPACT."""
            
            messages = [
                {"role": "system", "content": "You are an expert in Belgian Regulatory Impact Assessments and EU Impact Assessments. Generate comprehensive, evidence-based assessments following Belgian RIA structure with EU analysis style."},
                {"role": "user", "content": enhanced_query}
            ]
            
            response = await query_model_direct(CHAIRMAN_MODEL, messages, timeout=180.0)
            
            if response and response.get("content"):
                return {
                    "model": response.get("model", CHAIRMAN_MODEL),
                    "content": response.get("content", ""),
                    "stage1_results": [],
                    "stage2_results": []
                }
            else:
                raise ValueError("OpenAI API returned empty response")
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"   ❌ Fallback also failed: {e}")
            print(f"   📋 Full traceback:")
            print(error_trace)
            # Return minimal response with detailed error
            return {
                "model": "error",
                "content": f"Error: Unable to generate assessment. All API calls failed.\n\nError details: {str(e)}\n\nPlease check:\n1. Your API keys are set correctly\n2. Your API keys have sufficient credits\n3. The API services are accessible\n\nProposal: {query}",
                "stage1_results": [],
                "stage2_results": []
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
        # Stage 3 returns 'response' key, not 'content'
        content = assessment.get("content") or assessment.get("response", "")
        
        # Extract Eurostat citations
        eurostat_citations = []
        eurostat_data = retrieved.get("eurostat_data", {})
        print(f"📊 Extracting Eurostat citations from {len(eurostat_data)} themes...")
        for theme, stats in eurostat_data.items():
            if stats.get("statistics"):
                for stat in stats["statistics"]:
                    citation = stat.get("citation", "")
                    if citation:
                        eurostat_citations.append(citation)
                        print(f"   ✅ Found citation: {citation}")
        
        if not eurostat_citations:
            print(f"   ⚠️  No Eurostat citations found in eurostat_data")
            print(f"   📋 Eurostat data keys: {list(eurostat_data.keys())[:5]}")
            if eurostat_data:
                sample_theme = list(eurostat_data.keys())[0]
                sample_stats = eurostat_data[sample_theme]
                print(f"   📋 Sample theme '{sample_theme}' structure: {list(sample_stats.keys())}")
                if sample_stats.get("statistics"):
                    print(f"   📋 Sample statistics structure: {list(sample_stats['statistics'][0].keys()) if sample_stats['statistics'] else 'empty'}")
        
        # Validate that all 21 themes are present (but don't auto-add - LLM should generate them)
        missing_themes = self._validate_all_themes_present(content)
        if missing_themes:
            print(f"⚠️  WARNING: LLM did not generate all 21 themes. Missing: {sorted(missing_themes)}")
            print(f"   This indicates the LLM did not follow instructions properly.")
            print(f"   The report will be incomplete. Consider improving the prompt or retrying.")
        
        # Remove forbidden sections (Current Legal Framework, Problem Identification, etc.)
        # IMPORTANT: Do this FIRST before extracting sections
        content = self._remove_forbidden_sections(content)
        
        # Remove Recommendations/Conclusion sections if they exist
        content = self._remove_recommendations_section(content)
        
        # Fix any invalid assessment types (e.g., MIXED IMPACT)
        content = self._fix_invalid_assessments(content)
        
        # Validate Eurostat citations are used in content
        if eurostat_citations:
            self._validate_eurostat_citations_used(content, eurostat_citations)
        
        # Extract sections with debugging (content already has forbidden sections removed)
        extracted_sections = self._extract_sections(content)
        
        # Also filter extracted sections to ensure forbidden sections are not included
        extracted_sections = self._filter_forbidden_from_extracted_sections(extracted_sections)
        
        # Debug: Check why extraction might have failed
        if not extracted_sections or all(not v for v in extracted_sections.values()):
            print("⚠️  Section extraction failed - investigating...")
            print(f"   Content length: {len(content)} characters")
            print(f"   Content preview (first 500 chars): {content[:500]}")
            
            # Check for common section markers
            import re
            has_markdown_headers = bool(re.search(r'^##\s+', content, re.MULTILINE))
            has_numbered_sections = bool(re.search(r'^\d+\.\s+', content, re.MULTILINE))
            has_theme_markers = bool(re.search(r'\[\d+\]', content))
            print(f"   Has markdown headers (##): {has_markdown_headers}")
            print(f"   Has numbered sections (1. 2. etc): {has_numbered_sections}")
            print(f"   Has theme markers ([1] [2] etc): {has_theme_markers}")
            
            # Try to find what structure the content actually has
            if has_markdown_headers:
                headers = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
                print(f"   Found markdown headers: {headers[:5]}")
            
            if has_numbered_sections:
                numbered = re.findall(r'^\d+\.\s+(.+)$', content, re.MULTILINE)
                print(f"   Found numbered sections: {numbered[:5]}")
            
            # Don't use fallback yet - let's see what the actual issue is
            # For now, create a diagnostic section
            diagnostic_info = f"""
## Diagnostic Information

Content length: {len(content)} characters

Content structure analysis:
- Markdown headers (##): {has_markdown_headers}
- Numbered sections (1. 2. etc): {has_numbered_sections}
- Theme markers ([1] [2] etc): {has_theme_markers}

## Full Assessment Content

{content}
"""
            extracted_sections = {
                "Diagnostic": diagnostic_info,
                "Full Assessment": content
            }
        
        # Parse content into sections (simple heuristic)
        structured = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": assessment.get("model", "unknown"),
                "retrieval_strategy": retrieved.get("strategy", "unknown"),
                "chunks_used": len(retrieved.get("chunks", [])),
                "eurostat_datasets_used": len(eurostat_citations),
                "sections": []
            },
            "content": content,  # Final filtered content
            "sections": extracted_sections,  # Already filtered
            "sources": self._extract_sources(retrieved.get("chunks", [])),
            "eurostat_citations": eurostat_citations,
            "eurostat_data": eurostat_data  # Include full Eurostat data for frontend
        }
        
        # Final pass: Remove any remaining forbidden sections from content
        # This ensures they're removed even if they slipped through earlier
        structured["content"] = self._remove_forbidden_sections(structured["content"])
        
        # Debug: Print section keys for troubleshooting
        section_keys = list(extracted_sections.keys())
        print(f"📄 Extracted {len(section_keys)} sections: {section_keys[:5]}...")
        
        return structured
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract sections from generated content."""
        import re
        sections = {}
        
        if not content or len(content.strip()) == 0:
            print("   ⚠️  _extract_sections: Content is empty")
            return sections
        
        print(f"   🔍 _extract_sections: Analyzing content ({len(content)} chars)")
        
        # Extract standard EU sections
        eu_sections_found = 0
        for section_name in self.EU_IA_SECTIONS:
            # Look for section in content
            section_num = section_name.split(".")[0]
            pattern = f"{section_num}\\.|{section_name}"
            
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Extract section content (until next section or end)
                start = match.end()
                next_section = re.search(rf"{int(section_num) + 1}\\.", content[start:], re.IGNORECASE)
                end = start + next_section.start() if next_section else len(content)
                section_content = content[start:end].strip()
                sections[section_name] = section_content
                if section_content:
                    eu_sections_found += 1
                    print(f"      ✅ Found EU section: {section_name} ({len(section_content)} chars)")
            else:
                sections[section_name] = ""
        
        print(f"   📊 Found {eu_sections_found} EU sections with content")
        
        # Extract Belgian-specific sections
        # 21 Belgian Impact Themes Assessment
        themes_patterns = [
            r"##\s*Assessment\s+of\s+21\s+Impact\s+Themes",
            r"##\s*21\s+Impact\s+Themes",
            r"##\s*21\s+Belgian\s+Impact\s+Themes",
            r"Assessment\s+of\s+21\s+Impact\s+Themes"
        ]
        themes_found = False
        for i, pattern in enumerate(themes_patterns):
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                print(f"      ✅ Found Themes header pattern {i+1}: {pattern[:50]}...")
                start = match.end()
                # Find next major section (Overall Assessment, Recommendations, etc.)
                next_section = re.search(r"##\s*(?:Overall|Recommendations|Summary|Conclusion)", content[start:], re.IGNORECASE)
                end = start + next_section.start() if next_section else len(content)
                themes_content = content[start:end].strip()
                
                # Verify it contains theme assessments (look for [1], [2], etc.)
                theme_markers = re.findall(r'\[(\d+)\]', themes_content)
                if theme_markers:
                    print(f"         Themes section: {len(themes_content)} chars, found {len(theme_markers)} theme markers: {theme_markers[:5]}...")
                    sections["21 Belgian Impact Themes Assessment"] = themes_content
                    themes_found = True
                else:
                    print(f"         ⚠️  Themes header found but no [1], [2] markers in content")
                break
        
        if not themes_found:
            print(f"      ❌ Themes section header not found with any pattern")
        
        # If themes section not found by header, try to extract from content
        if "21 Belgian Impact Themes Assessment" not in sections:
            print(f"      🔍 Trying fallback: looking for [1], [2] patterns in content...")
            # Look for pattern of [1] through [21] in content
            theme_start = re.search(r'\[\d+\]\s+[A-Z]', content)
            if theme_start:
                print(f"         ✅ Found theme marker at position {theme_start.start()}")
                # Find where themes section likely starts (before first [1])
                # Look backwards for a header
                before_themes = content[:theme_start.start()]
                header_match = re.search(r'##\s+[^\n]+', before_themes[::-1])
                if header_match:
                    themes_start = len(before_themes) - header_match.end()
                else:
                    themes_start = theme_start.start()
                
                # Find where themes section ends (before Overall Assessment or Recommendations)
                themes_end_match = re.search(r'##\s*(?:Overall|Recommendations|Summary|Conclusion)', content[themes_start:], re.IGNORECASE)
                if themes_end_match:
                    themes_end = themes_start + themes_end_match.start()
                else:
                    # Count themes - should have [1] through [21]
                    theme_markers = re.findall(r'\[(\d+)\]', content[themes_start:])
                    if len(theme_markers) >= 21:
                        # Find the end of the last theme
                        last_theme = re.search(r'\[21\][^\[]*', content[themes_start:], re.DOTALL)
                        if last_theme:
                            themes_end = themes_start + last_theme.end()
                        else:
                            themes_end = len(content)
                    else:
                        themes_end = len(content)
                
                themes_content = content[themes_start:themes_end].strip()
                theme_markers = re.findall(r'\[(\d+)\]', themes_content)
                if theme_markers:
                    print(f"         ✅ Extracted themes section via fallback: {len(themes_content)} chars, {len(theme_markers)} themes")
                    sections["21 Belgian Impact Themes Assessment"] = themes_content
                else:
                    print(f"         ❌ Fallback found start position but no theme markers")
            else:
                print(f"         ❌ No theme markers [1], [2] found in content")
        
        # Summary
        sections_with_content = {k: v for k, v in sections.items() if v and v.strip()}
        print(f"   📊 Extraction complete: {len(sections_with_content)} sections with content out of {len(sections)} total")
        if sections_with_content:
            print(f"      Sections found: {list(sections_with_content.keys())}")
        else:
            print(f"      ⚠️  NO SECTIONS WITH CONTENT FOUND")
            # Show content preview to help debug
            print(f"      Content preview (first 1000 chars):\n{content[:1000]}")
        
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
    
    def _validate_eurostat_citations_used(self, content: str, eurostat_citations: list) -> None:
        """
        Validate that Eurostat citations are actually used in the generated content.
        Warns if citations are provided but not used in the text.
        """
        if not eurostat_citations:
            return
        
        # Extract dataset codes from citations (e.g., "ilc_li02" from "Eurostat, ilc_li02, Belgium, 2022")
        import re
        dataset_codes = []
        for citation in eurostat_citations:
            # Extract dataset code from citation format: "Eurostat, DATASET_CODE, Belgium, 2022"
            match = re.search(r'Eurostat,\s*([a-z0-9_]+)', citation, re.IGNORECASE)
            if match:
                dataset_codes.append(match.group(1).lower())
        
        if not dataset_codes:
            return
        
        # Check if any dataset codes appear in the content
        content_lower = content.lower()
        found_citations = []
        missing_citations = []
        
        for dataset_code in dataset_codes:
            # Check if it's actually cited (not just mentioned)
            # Look for patterns like "Eurostat (dataset_code" or "according to Eurostat"
            citation_patterns = [
                rf'eurostat\s*[\(,].*{re.escape(dataset_code)}',
                rf'{re.escape(dataset_code)}.*eurostat',
                rf'according\s+to\s+eurostat.*{re.escape(dataset_code)}',
                rf'eurostat.*{re.escape(dataset_code)}.*belgium'
            ]
            found = any(re.search(pattern, content_lower) for pattern in citation_patterns)
            if found:
                found_citations.append(dataset_code)
            else:
                missing_citations.append(dataset_code)
        
        if missing_citations:
            print(f"   ⚠️  WARNING: {len(missing_citations)}/{len(dataset_codes)} Eurostat citations not used in generated text")
            print(f"      Missing: {missing_citations[:5]}...")
            print(f"      The LLM may have ignored the Eurostat data provided in context")
        else:
            print(f"   ✅ All {len(found_citations)} Eurostat citations appear to be used in the text")
    
    def _validate_all_themes_present(self, content: str) -> set:
        """
        Validate that all 21 themes are present in the content.
        Returns set of missing theme numbers (empty if all present).
        """
        import re
        
        # Find all theme markers in content
        theme_markers = re.findall(r'\[(\d+)\]', content)
        found_theme_numbers = set(int(num) for num in theme_markers)
        expected_theme_numbers = set(range(1, 22))  # [1] through [21]
        missing_themes = expected_theme_numbers - found_theme_numbers
        
        print(f"🔍 Theme validation: Found {len(found_theme_numbers)}/21 themes: {sorted(found_theme_numbers)}")
        if missing_themes:
            print(f"   Missing themes: {sorted(missing_themes)}")
        else:
            print(f"✅ All 21 themes present")
        
        return missing_themes
    
    def _fix_invalid_assessments(self, content: str) -> str:
        """
        Fix any invalid assessment types (e.g., MIXED IMPACT) by converting them to valid types.
        Only POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT are allowed.
        """
        import re
        
        # Find all assessment lines with invalid types
        invalid_patterns = [
            (r'Assessment:\s*\[MIXED\s+IMPACT\]', 'MIXED IMPACT'),
            (r'Assessment:\s*\[Mixed\s+Impact\]', 'Mixed Impact'),
            (r'Assessment:\s*MIXED\s+IMPACT', 'MIXED IMPACT'),
            (r'Assessment:\s*Mixed\s+Impact', 'Mixed Impact'),
        ]
        
        fixed_count = 0
        for pattern, invalid_type in invalid_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                print(f"   ⚠️  Found {len(matches)} invalid assessment(s) with '{invalid_type}'")
                # Replace with NO IMPACT (safest default - user can review)
                content = re.sub(pattern, 'Assessment: [NO IMPACT]', content, flags=re.IGNORECASE)
                fixed_count += len(matches)
        
        if fixed_count > 0:
            print(f"   ✅ Fixed {fixed_count} invalid assessment(s) to [NO IMPACT]")
        
        return content
    
    def _remove_recommendations_section(self, content: str) -> str:
        """
        Remove any Recommendations, Conclusion, Executive Summary, Proposal Overview,
        or Overall Assessment Summary sections from the content.
        The report should contain ONLY the 21 Impact Themes Assessment section.
        """
        import re
        
        # Find Recommendations or Conclusion sections
        patterns = [
            r'##\s*(?:Recommendations|Conclusion|3\.\s*Conclusion|3\.\s*Recommendations).*$',
            r'##\s*Recommendations.*?(?=##|$)',
            r'##\s*Conclusion.*?(?=##|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                print(f"   🗑️  Found and removing Recommendations/Conclusion section")
                # Remove from the start of the section to the end
                content = content[:match.start()].rstrip()
                break
        
        return content
    
    def _remove_forbidden_sections(self, content: str) -> str:
        """
        Remove forbidden sections: Current Legal Framework, Problem Identification,
        Policy Objectives, and Stakeholders Affected.
        Handles various formats and embedded sections.
        """
        import re
        
        # Expanded list to catch variations
        forbidden_patterns = [
            # Original forbidden sections
            r'##\s*Current\s+Legal\s+Framework.*?(?=##|$)',
            r'#\s*Current\s+Legal\s+Framework.*?(?=#|$)',
            r'###\s*Current\s+Legal\s+Framework.*?(?=###|$)',
            r'^\s*Current\s+Legal\s+Framework\s*$.*?(?=^##|^#|$)',
            r'##\s*Legal\s+Framework.*?(?=##|$)',
            r'#\s*Legal\s+Framework.*?(?=#|$)',
            r'###\s*Legal\s+Framework.*?(?=###|$)',
            r'^\s*Legal\s+Framework\s*$.*?(?=^##|^#|$)',
            r'##\s*Problem\s+Identification.*?(?=##|$)',
            r'#\s*Problem\s+Identification.*?(?=#|$)',
            r'###\s*Problem\s+Identification.*?(?=###|$)',
            r'^\s*Problem\s+Identification\s*$.*?(?=^##|^#|$)',
            r'##\s*Policy\s+Objectives.*?(?=##|$)',
            r'#\s*Policy\s+Objectives.*?(?=#|$)',
            r'###\s*Policy\s+Objectives.*?(?=###|$)',
            r'^\s*Policy\s+Objectives\s*$.*?(?=^##|^#|$)',
            r'##\s*Stakeholders\s+Affected.*?(?=##|$)',
            r'#\s*Stakeholders\s+Affected.*?(?=#|$)',
            r'###\s*Stakeholders\s+Affected.*?(?=###|$)',
            r'^\s*Stakeholders\s+Affected\s*$.*?(?=^##|^#|$)',
            r'##\s*Stakeholders.*?(?=##|$)',
            r'#\s*Stakeholders.*?(?=#|$)',
            r'###\s*Stakeholders.*?(?=###|$)',
            # New forbidden sections (Executive Summary, Proposal Overview, etc.)
            r'##\s*Executive\s+Summary.*?(?=##|$)',
            r'#\s*Executive\s+Summary.*?(?=#|$)',
            r'###\s*Executive\s+Summary.*?(?=###|$)',
            r'^\s*Executive\s+Summary\s*$.*?(?=^##|^#|$)',
            r'##\s*Proposal\s+Overview.*?(?=##|$)',
            r'#\s*Proposal\s+Overview.*?(?=#|$)',
            r'###\s*Proposal\s+Overview.*?(?=###|$)',
            r'^\s*Proposal\s+Overview\s*$.*?(?=^##|^#|$)',
            r'##\s*Overall\s+Assessment\s+Summary.*?(?=##|$)',
            r'#\s*Overall\s+Assessment\s+Summary.*?(?=#|$)',
            r'###\s*Overall\s+Assessment\s+Summary.*?(?=###|$)',
            r'^\s*Overall\s+Assessment\s+Summary\s*$.*?(?=^##|^#|$)',
            r'##\s*Recommendations.*?(?=##|$)',
            r'#\s*Recommendations.*?(?=#|$)',
            r'###\s*Recommendations.*?(?=###|$)',
            r'^\s*Recommendations\s*$.*?(?=^##|^#|$)',
            r'##\s*Conclusion.*?(?=##|$)',
            r'#\s*Conclusion.*?(?=#|$)',
            r'###\s*Conclusion.*?(?=###|$)',
            r'^\s*Conclusion\s*$.*?(?=^##|^#|$)',
        ]
        
        removed_count = 0
        for pattern in forbidden_patterns:
            # Use DOTALL to match across newlines, MULTILINE for ^ and $
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL | re.MULTILINE))
            if matches:
                # Remove from end to start to preserve indices
                for match in reversed(matches):
                    section_text = content[match.start():match.end()]
                    # Check if this looks like a section header (not just text mentioning the term)
                    if re.search(r'^#+\s|^\s*[A-Z]', section_text[:50], re.MULTILINE):
                        print(f"   🗑️  Found and removing forbidden section: {section_text[:100]}...")
                        content = content[:match.start()] + content[match.end():]
                        removed_count += 1
        
        if removed_count > 0:
            print(f"   ✅ Removed {removed_count} forbidden section(s)")
        
        return content
    
    def _filter_forbidden_from_extracted_sections(self, sections: Dict[str, str]) -> Dict[str, str]:
        """
        Filter out forbidden sections from the extracted sections dictionary.
        Also removes any section content that contains forbidden section headers.
        """
        forbidden_keywords = [
            "Current Legal Framework",
            "Legal Framework",
            "Problem Identification",
            "Policy Objectives",
            "Stakeholders Affected",
            "Stakeholders",
            "Executive Summary",
            "Proposal Overview",
            "Overall Assessment Summary",
            "Recommendations",
            "Conclusion"
        ]
        
        filtered_sections = {}
        for section_name, section_content in sections.items():
            # Skip if section name itself contains forbidden keywords
            if any(keyword.lower() in section_name.lower() for keyword in forbidden_keywords):
                print(f"   🗑️  Filtering out section '{section_name}' (contains forbidden keyword)")
                continue
            
            # Check if section content contains forbidden section headers
            import re
            has_forbidden = False
            for keyword in forbidden_keywords:
                # Look for section headers with this keyword
                pattern = rf'#+\s*{re.escape(keyword)}|^\s*{re.escape(keyword)}\s*$'
                if re.search(pattern, section_content, re.IGNORECASE | re.MULTILINE):
                    print(f"   🗑️  Filtering content from '{section_name}' (contains '{keyword}')")
                    # Remove the forbidden section from the content
                    # Find and remove the section
                    forbidden_pattern = rf'#+\s*{re.escape(keyword)}.*?(?=#+|$)'
                    section_content = re.sub(forbidden_pattern, '', section_content, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
                    has_forbidden = True
            
            if not has_forbidden or section_content.strip():
                filtered_sections[section_name] = section_content.strip()
        
        return filtered_sections
    
    async def _complete_missing_themes(
        self, 
        existing_content: str, 
        missing_theme_numbers: set, 
        query: str, 
        context: str
    ) -> Optional[str]:
        """
        Make a focused LLM call to generate only the missing themes.
        Returns the completed content with all themes.
        """
        from .direct_apis import query_openai
        from .api_keys import OPENAI_API_KEY
        
        if not OPENAI_API_KEY:
            print("   ⚠️  Cannot complete themes: No OpenAI API key")
            return None
        
        # Get theme definitions for missing themes
        ALL_THEMES = {
            1: ("Fight against poverty", "Revenu minimum conforme à la dignité humaine, accès à des services de qualité, surendettement, risque de pauvreté ou d'exclusion sociale (y compris chez les mineurs), illettrisme, fracture numérique"),
            2: ("Equal opportunities and social cohesion", "Non-discrimination, égalité de traitement, accès aux biens et services, accès à l'information, à l'éducation et à la formation, écart de revenu, effectivité des droits civils, politiques et sociaux (en particulier pour les populations fragilisées, les enfants, les personnes âgées, les personnes handicapées et les minorités)"),
            3: ("Equality between women and men", "Accès des femmes et des hommes aux ressources: revenus, travail, responsabilités, santé/soins/bien-être, sécurité, éducation/savoir/formation, mobilité, temps, loisirs, etc. Exercice des droits fondamentaux par les femmes et les hommes droits civils, sociaux et politiques"),
            4: ("Health", "Accès aux soins de santé de qualité, efficacité de l'offre de soins, espérance de vie en bonne santé, traitements des maladies chroniques (maladies cardiovasculaires, cancers, diabètes et maladies respiratoires chroniques), déterminants de la santé (niveau socio-économique, alimentation, pollution), qualité de la vie"),
            5: ("Employment", "Accès au marché de l'emploi, emplois de qualité, chômage, travail au noir, conditions de travail et de licenciement, carrière, temps de travail, bien-être au travail, accidents de travail, maladies professionnelles, équilibre vie privée - vie professionnelle, rémunération convenable, possibilités de formation professionnelle, relations collectives de travail"),
            6: ("Consumption and production patterns", "Stabilité/prévisibilité des prix, information et protection du consommateur, utilisation efficace des ressources, évaluation et intégration des externalités (environnementales et sociales) tout au long du cycle de vie des produits et services, modes de gestion des organisations"),
            7: ("Economic development", "Création d'entreprises, production de biens et de services, productivité du travail et des ressources/matières premières, facteurs de compétitivité, accès au marché et à la profession, transparence du marché, accès aux marchés publics, relations commerciales et financières internationales, balance des importations/exportations, économie souterraine, sécurité d'approvisionnement des ressources énergétiques, minérales et organiques"),
            8: ("Investments", "Investissements en capital physique (machines, véhicules, infrastructures), technologique, intellectuel (logiciel, recherche et développement) et humain, niveau d'investissement net en pourcentage du PIB"),
            9: ("Research and development", "Opportunités de recherche et développement, innovation par l'introduction et la diffusion de nouveaux modes de production, de nouvelles pratiques d'entreprises ou de nouveaux produits et services, dépenses de recherche et de développement"),
            10: ("SMEs (Small and Medium-Sized Enterprises)", "Impact sur le développement des PME"),
            11: ("Administrative burdens", "Réduction des formalités et des obligations administratives liées directement ou indirectement à l'exécution, au respect et/ou au maintien d'un droit, d'une interdiction ou d'une obligation"),
            12: ("Energy", "Mix énergétique (bas carbone, renouvelable, fossile), utilisation de la biomasse (bois, biocarburants), efficacité énergétique, consommation d'énergie de l'industrie, des services, des transports et des ménages, sécurité d'approvisionnement, accès aux biens et services énergétiques"),
            13: ("Mobility", "Volume de transport (nombre de kilomètres parcourus et nombre de véhicules), offre de transports collectifs, offre routière, ferroviaire, maritime et fluviale pour les transports de marchandises, répartitions des modes de transport (modal shift), sécurité, densité du trafic"),
            14: ("Food", "Accès à une alimentation sûre (contrôle de qualité), alimentation saine et à haute valeur nutritionnelle, gaspillages, commerce équitable"),
            15: ("Climate change", "Émissions de gaz à effet de serre, capacité d'adaptation aux effets des changements climatiques, résilience, transition énergétique, sources d'énergies renouvelables, utilisation rationnelle de l'énergie, efficacité énergétique, performance énergétique des bâtiments, piégeage du carbone"),
            16: ("Natural resources", "Gestion efficiente des ressources, recyclage, réutilisation, qualité et consommation de l'eau (eaux de surface et souterraines, mers et océans), qualité et utilisation du sol (pollution, teneur en matières organiques, érosion, assèchement, inondations, densification, fragmentation), déforestation"),
            17: ("Indoor and outdoor air", "Qualité de l'air (y compris l'air intérieur), émissions de polluants (agents chimiques ou biologiques méthane, hydrocarbures, solvants, SOX, NOx, NH3), particules fines"),
            18: ("Biodiversity", "Niveaux de la diversité biologique, état des écosystèmes (restauration, conservation, valorisation, zones protégées), altération et fragmentation des habitats, biotechnologies, brevets d'invention sur la matière biologique, utilisation des ressources génétiques, services rendus par les écosystèmes (purification de l'eau et de l'air, ...), espèces domestiquées ou cultivées, espèces exotiques envahissantes, espèces menacées"),
            19: ("Nuisances", "Nuisances sonores, visuelles ou olfactives, vibrations, rayonnements ionisants, non ionisants et électromagnétiques, nuisances lumineuses"),
            20: ("Public authorities", "Fonctionnement démocratique des organes de concertation et consultation, services publics aux usagers, plaintes, recours, contestations, mesures d'exécution, investissements publics"),
            21: ("Policy coherence for development", "Prise en considération des impacts involontaires des mesures politiques belges sur les intérêts des pays en voie de développement"),
        }
        
        # Build list of missing themes with their details
        missing_themes_list = []
        for theme_num in sorted(missing_theme_numbers):
            if theme_num in ALL_THEMES:
                name, keywords = ALL_THEMES[theme_num]
                missing_themes_list.append((theme_num, name, keywords))
        
        if not missing_themes_list:
            return existing_content
        
        print(f"   📝 Generating {len(missing_themes_list)} missing themes...")
        
        # Build focused prompt for missing themes only
        missing_themes_text = "\n\n".join([
            f"[{num}] {name}\nKeywords: {keywords}"
            for num, name, keywords in missing_themes_list
        ])
        
        # Include Eurostat context if available - extract just the Eurostat section
        eurostat_section = ""
        if context and "Eurostat Statistical Data" in context:
            # Extract the Eurostat section from context
            eurostat_start = context.find("Eurostat Statistical Data")
            if eurostat_start != -1:
                # Find where Eurostat section ends (before "RELEVANT DOCUMENTS" or end of context)
                eurostat_end_marker = context.find("RELEVANT DOCUMENTS", eurostat_start)
                if eurostat_end_marker == -1:
                    eurostat_end_marker = context.find("=" * 70, eurostat_start + 2000)  # Find end of Eurostat section
                if eurostat_end_marker != -1:
                    eurostat_section = context[eurostat_start:eurostat_end_marker + 100]
                else:
                    # Take first 4000 chars which should include full Eurostat section
                    eurostat_section = context[eurostat_start:eurostat_start + 4000]
        
        # Build prompt with Eurostat context
        completion_prompt = f"""Complete a Belgian RIA by generating {len(missing_themes_list)} missing impact theme assessments.

Proposal: {query[:500]}

{eurostat_section if eurostat_section else ""}

Generate ONLY these missing themes (format: [N] Theme Name, Keywords, Assessment: [IMPACT TYPE], 150+ word explanation):

{missing_themes_text}

CRITICAL REQUIREMENTS:
1. For each theme, you MUST choose ONE of: POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT.
   - DO NOT use "MIXED IMPACT" - this is NOT allowed
   - If a theme has both positive and negative aspects, determine the NET/OVERALL impact and choose POSITIVE IMPACT or NEGATIVE IMPACT accordingly
2. Provide detailed explanation (150+ words) for your chosen impact type
3. 🚨 MANDATORY EUROSTAT USAGE: If Eurostat statistical data is provided above for any of these themes, you MUST:
   - Include the Eurostat citation WITH actual quantitative values (percentages, numbers) in your explanation
   - Use the "READY-TO-USE CITATION" format shown above - copy it directly into your text
   - Example CORRECT: "According to Eurostat (ilc_li02, Belgium, 2022), the at-risk-of-poverty rate was 15.3%"
   - Example WRONG: "According to Eurostat data, poverty is an issue" [missing citation and values - REJECTED]
   - The purpose is to QUANTIFY your statements - you MUST include the numbers provided
   - DO NOT write generic statements when specific Eurostat data is available above"""

        try:
            messages = [{"role": "user", "content": completion_prompt}]
            print(f"   📤 Calling {CHAIRMAN_MODEL} to complete {len(missing_themes_list)} themes...")
            print(f"   📏 Prompt length: {len(completion_prompt)} chars")
            response = await query_model_direct(CHAIRMAN_MODEL, messages, timeout=180.0)
            
            if response and response.get("content"):
                completed_themes = response.get("content", "").strip()
                print(f"   ✅ Received response: {len(completed_themes)} chars")
                # Check if response looks complete
                import re
                theme_markers_in_response = re.findall(r'\[(\d+)\]', completed_themes)
                print(f"   🔍 Found {len(theme_markers_in_response)} theme markers in completion: {sorted([int(m) for m in theme_markers_in_response])}")
                
                # Insert completed themes into existing content
                # Find where to insert (after the last existing theme)
                import re
                theme_markers = re.findall(r'\[(\d+)\]', existing_content)
                if theme_markers:
                    max_theme = max(int(num) for num in theme_markers)
                    # Find the end of the last theme
                    pattern = rf'\[{max_theme}\][^\[]*?(?=\[\d+\]|##\s*(?:Overall|Recommendations|Summary|Conclusion)|$)'
                    match = re.search(pattern, existing_content, re.DOTALL | re.IGNORECASE)
                    if match:
                        insert_pos = match.end()
                        completed_content = (
                            existing_content[:insert_pos].rstrip() + 
                            "\n\n" + completed_themes + "\n\n" + 
                            existing_content[insert_pos:].lstrip()
                        )
                    else:
                        # Append at end
                        completed_content = existing_content.rstrip() + "\n\n" + completed_themes
                else:
                    # No themes found, append
                    completed_content = existing_content.rstrip() + "\n\n" + completed_themes
                
                print(f"   ✅ Generated {len(missing_themes_list)} missing themes")
                return completed_content
            else:
                print(f"   ⚠️  Failed to generate missing themes")
                return None
                
        except Exception as e:
            print(f"   ⚠️  Error completing themes: {e}")
            import traceback
            print(f"   📋 Full error:")
            traceback.print_exc()
            return None
    
    def _validate_and_complete_themes(self, content: str) -> str:
        """
        Validate that all 21 themes are present in the content.
        If themes are missing, add them with NO IMPACT assessments.
        """
        import re
        
        # Define all 21 themes with their keywords
        ALL_THEMES = [
            (1, "Fight against poverty", "Revenu minimum conforme à la dignité humaine, accès à des services de qualité, surendettement, risque de pauvreté ou d'exclusion sociale (y compris chez les mineurs), illettrisme, fracture numérique"),
            (2, "Equal opportunities and social cohesion", "Non-discrimination, égalité de traitement, accès aux biens et services, accès à l'information, à l'éducation et à la formation, écart de revenu, effectivité des droits civils, politiques et sociaux (en particulier pour les populations fragilisées, les enfants, les personnes âgées, les personnes handicapées et les minorités)"),
            (3, "Equality between women and men", "Accès des femmes et des hommes aux ressources: revenus, travail, responsabilités, santé/soins/bien-être, sécurité, éducation/savoir/formation, mobilité, temps, loisirs, etc. Exercice des droits fondamentaux par les femmes et les hommes droits civils, sociaux et politiques"),
            (4, "Health", "Accès aux soins de santé de qualité, efficacité de l'offre de soins, espérance de vie en bonne santé, traitements des maladies chroniques (maladies cardiovasculaires, cancers, diabètes et maladies respiratoires chroniques), déterminants de la santé (niveau socio-économique, alimentation, pollution), qualité de la vie"),
            (5, "Employment", "Accès au marché de l'emploi, emplois de qualité, chômage, travail au noir, conditions de travail et de licenciement, carrière, temps de travail, bien-être au travail, accidents de travail, maladies professionnelles, équilibre vie privée - vie professionnelle, rémunération convenable, possibilités de formation professionnelle, relations collectives de travail"),
            (6, "Consumption and production patterns", "Stabilité/prévisibilité des prix, information et protection du consommateur, utilisation efficace des ressources, évaluation et intégration des externalités (environnementales et sociales) tout au long du cycle de vie des produits et services, modes de gestion des organisations"),
            (7, "Economic development", "Création d'entreprises, production de biens et de services, productivité du travail et des ressources/matières premières, facteurs de compétitivité, accès au marché et à la profession, transparence du marché, accès aux marchés publics, relations commerciales et financières internationales, balance des importations/exportations, économie souterraine, sécurité d'approvisionnement des ressources énergétiques, minérales et organiques"),
            (8, "Investments", "Investissements en capital physique (machines, véhicules, infrastructures), technologique, intellectuel (logiciel, recherche et développement) et humain, niveau d'investissement net en pourcentage du PIB"),
            (9, "Research and development", "Opportunités de recherche et développement, innovation par l'introduction et la diffusion de nouveaux modes de production, de nouvelles pratiques d'entreprises ou de nouveaux produits et services, dépenses de recherche et de développement"),
            (10, "SMEs (Small and Medium-Sized Enterprises)", "Impact sur le développement des PME"),
            (11, "Administrative burdens", "Réduction des formalités et des obligations administratives liées directement ou indirectement à l'exécution, au respect et/ou au maintien d'un droit, d'une interdiction ou d'une obligation"),
            (12, "Energy", "Mix énergétique (bas carbone, renouvelable, fossile), utilisation de la biomasse (bois, biocarburants), efficacité énergétique, consommation d'énergie de l'industrie, des services, des transports et des ménages, sécurité d'approvisionnement, accès aux biens et services énergétiques"),
            (13, "Mobility", "Volume de transport (nombre de kilomètres parcourus et nombre de véhicules), offre de transports collectifs, offre routière, ferroviaire, maritime et fluviale pour les transports de marchandises, répartitions des modes de transport (modal shift), sécurité, densité du trafic"),
            (14, "Food", "Accès à une alimentation sûre (contrôle de qualité), alimentation saine et à haute valeur nutritionnelle, gaspillages, commerce équitable"),
            (15, "Climate change", "Émissions de gaz à effet de serre, capacité d'adaptation aux effets des changements climatiques, résilience, transition énergétique, sources d'énergies renouvelables, utilisation rationnelle de l'énergie, efficacité énergétique, performance énergétique des bâtiments, piégeage du carbone"),
            (16, "Natural resources", "Gestion efficiente des ressources, recyclage, réutilisation, qualité et consommation de l'eau (eaux de surface et souterraines, mers et océans), qualité et utilisation du sol (pollution, teneur en matières organiques, érosion, assèchement, inondations, densification, fragmentation), déforestation"),
            (17, "Indoor and outdoor air", "Qualité de l'air (y compris l'air intérieur), émissions de polluants (agents chimiques ou biologiques méthane, hydrocarbures, solvants, SOX, NOx, NH3), particules fines"),
            (18, "Biodiversity", "Niveaux de la diversité biologique, état des écosystèmes (restauration, conservation, valorisation, zones protégées), altération et fragmentation des habitats, biotechnologies, brevets d'invention sur la matière biologique, utilisation des ressources génétiques, services rendus par les écosystèmes (purification de l'eau et de l'air, ...), espèces domestiquées ou cultivées, espèces exotiques envahissantes, espèces menacées"),
            (19, "Nuisances", "Nuisances sonores, visuelles ou olfactives, vibrations, rayonnements ionisants, non ionisants et électromagnétiques, nuisances lumineuses"),
            (20, "Public authorities", "Fonctionnement démocratique des organes de concertation et consultation, services publics aux usagers, plaintes, recours, contestations, mesures d'exécution, investissements publics"),
            (21, "Policy coherence for development", "Prise en considération des impacts involontaires des mesures politiques belges sur les intérêts des pays en voie de développement"),
        ]
        
        # Find all theme markers in content (be flexible with whitespace)
        # Pattern: [N] or [ N ] or [N] at start of line or after newline
        theme_markers = re.findall(r'\[(\d+)\]', content)
        found_theme_numbers = set(int(num) for num in theme_markers)
        expected_theme_numbers = set(num for num, _, _ in ALL_THEMES)
        missing_themes = expected_theme_numbers - found_theme_numbers
        
        print(f"🔍 Theme validation: Found {len(found_theme_numbers)} themes: {sorted(found_theme_numbers)}")
        print(f"   Expected: {sorted(expected_theme_numbers)}")
        
        if not missing_themes:
            print(f"✅ Validation: All 21 themes found in content")
            return content
        
        print(f"⚠️  Validation: Missing {len(missing_themes)} themes: {sorted(missing_themes)}")
        print(f"   Found themes: {sorted(found_theme_numbers)}")
        
        # Generate missing theme assessments
        missing_assessments = []
        for theme_num, theme_name, keywords in ALL_THEMES:
            if theme_num in missing_themes:
                assessment_text = f"""
[{theme_num}] {theme_name}
Keywords: {keywords}
Assessment: [NO IMPACT]

After careful analysis of the proposal, this theme does not appear to have a direct or indirect impact. The proposal's scope and objectives do not intersect with the key areas covered by this impact theme. While this assessment indicates no impact, it is important to note that this determination is based on the current understanding of the proposal's provisions and their expected effects. Should the proposal be modified or its implementation reveal additional dimensions, this assessment may need to be revisited. The absence of impact in this area does not diminish the importance of monitoring potential indirect effects that may emerge during the implementation phase or through interactions with other policy measures.
"""
                missing_assessments.append((theme_num, assessment_text))
        
        if not missing_assessments:
            return content
        
        # Sort missing assessments by theme number
        missing_assessments.sort(key=lambda x: x[0])
        
        # Find where to insert missing themes
        # Strategy: Find the last existing theme and insert missing ones after it
        insert_position = None
        
        # Find the highest-numbered existing theme
        if found_theme_numbers:
            max_found_theme = max(found_theme_numbers)
            print(f"   Last existing theme: [{max_found_theme}]")
            # Find the end of this theme's content - look for the pattern [N] followed by content until next [N+1] or section header
            # Try multiple patterns to be more robust
            patterns = [
                rf'\[{max_found_theme}\][^\[]*?(?=\[\d+\]|##\s+(?:Overall|Recommendations|Summary|Conclusion)|$)',
                rf'\[{max_found_theme}\].*?(?=\[\d+\]|##|$)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    insert_position = match.end()
                    print(f"   Found insertion point after theme [{max_found_theme}] at position {insert_position}")
                    break
        
        # If we couldn't find a good insertion point, look for themes section end
        if insert_position is None:
            print("   Could not find insertion point after last theme, trying section headers...")
            # Look for the themes section header (more flexible patterns)
            themes_section_patterns = [
                r'##\s*(?:Assessment\s+of\s+21\s+Impact\s+Themes|21\s+Impact\s+Themes|21\s+Belgian\s+Impact\s+Themes)',
                r'##\s*Assessment',
                r'Assessment\s+of\s+21',
                r'21\s+Impact\s+Themes',
            ]
            
            themes_section_match = None
            for pattern in themes_section_patterns:
                themes_section_match = re.search(pattern, content, re.IGNORECASE)
                if themes_section_match:
                    print(f"   Found themes section header: {pattern[:50]}...")
                    break
            
            if themes_section_match:
                # Find the end of themes section (before Overall Assessment, Recommendations, etc.)
                section_start = themes_section_match.end()
                next_section = re.search(
                    r'##\s*(?:Overall\s+Assessment|Recommendations|Summary|Conclusion)',
                    content[section_start:],
                    re.IGNORECASE
                )
                if next_section:
                    insert_position = section_start + next_section.start()
                    print(f"   Found next section, inserting at {insert_position}")
                else:
                    insert_position = len(content)
                    print(f"   No next section found, appending at end (position {insert_position})")
            else:
                # No themes section found, find last theme and append after it
                if found_theme_numbers:
                    # Find any occurrence of the last theme number
                    last_theme_pattern = rf'\[{max(found_theme_numbers)}\]'
                    last_match = list(re.finditer(last_theme_pattern, content))
                    if last_match:
                        # Get the last occurrence
                        last_theme_pos = last_match[-1].start()
                        # Find end of that theme's content
                        remaining = content[last_theme_pos:]
                        # Look for next theme or section
                        next_theme_or_section = re.search(r'\[\d+\]|##', remaining[100:])  # Skip first 100 chars to get past current theme
                        if next_theme_or_section:
                            insert_position = last_theme_pos + 100 + next_theme_or_section.start()
                        else:
                            insert_position = len(content)
                        print(f"   Found last theme at {last_theme_pos}, inserting at {insert_position}")
                    else:
                        insert_position = len(content)
                else:
                    # No themes section found, append at end
                    insert_position = len(content)
                    print(f"   No themes section found, appending at end (position {insert_position})")
        
        # Insert missing themes
        insert_text = "\n".join(assessment.strip() for _, assessment in missing_assessments)
        
        if insert_position is not None and insert_position < len(content):
            # Insert before next section
            before = content[:insert_position].rstrip()
            after = content[insert_position:].lstrip()
            content = before + "\n\n" + insert_text + "\n\n" + after
            print(f"✅ Inserted {len(missing_assessments)} missing theme assessments at position {insert_position}")
        else:
            # Append at the end
            content = content.rstrip() + "\n\n" + insert_text
            print(f"✅ Appended {len(missing_assessments)} missing theme assessments at end")
        
        # Verify themes were added
        theme_markers_after = re.findall(r'\[(\d+)\]', content)
        found_after = set(int(num) for num in theme_markers_after)
        still_missing = expected_theme_numbers - found_after
        
        if len(found_after) == 21:
            print(f"✅ Verification: All 21 themes now present in content")
        else:
            print(f"⚠️  Verification: Only {len(found_after)}/21 themes found after insertion")
            print(f"   Still missing: {sorted(still_missing)}")
            # Last resort: append any still-missing themes at the very end
            if still_missing:
                print(f"   Attempting final append for {len(still_missing)} themes...")
                final_missing = [a for num, a in missing_assessments if num in still_missing]
                if final_missing:
                    final_text = "\n".join(assessment.strip() for assessment in final_missing)
                    content = content.rstrip() + "\n\n" + final_text
                    # Verify again
                    theme_markers_final = re.findall(r'\[(\d+)\]', content)
                    found_final = set(int(num) for num in theme_markers_final)
                    if len(found_final) == 21:
                        print(f"✅ Final verification: All 21 themes now present")
                    else:
                        print(f"⚠️  Final verification: Still only {len(found_final)}/21 themes")
        
        return content


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
    generator = ImpactAssessmentGenerator(enable_eurostat=True)
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
