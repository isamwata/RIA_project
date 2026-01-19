"""
LangGraph orchestration for RIA Impact Assessment Generation.

This module implements a fully orchestrated workflow that:
- Retrieves context from both vector store and knowledge graph
- Runs LLM Council (3-stage process) for generation
- Structures output into EU Impact Assessment format
- Updates knowledge base with new proposal
"""

import asyncio
from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from typing_extensions import NotRequired
import operator
from datetime import datetime
import json
import re
from pathlib import Path

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️  LangGraph not installed. Install with: pip install langgraph")

from .vector_store import VectorStore
from .knowledge_graph import KnowledgeGraphBuilder
from .council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final
)
from .config import CHAIRMAN_MODEL


# ============================================================================
# State Schema
# ============================================================================

class RIAState(TypedDict):
    """State schema for RIA generation workflow."""
    # Input
    proposal: str
    context: NotRequired[Dict[str, Any]]  # metadata: jurisdiction, category, year, etc.
    
    # Processing
    features: NotRequired[Dict[str, Any]]  # extracted features from proposal
    retrieval_strategy: NotRequired[str]  # "dense", "sparse", "hybrid", "graph-first"
    
    # Retrieval results
    vector_results: NotRequired[List[Dict[str, Any]]]
    graph_results: NotRequired[List[Dict[str, Any]]]
    merged_chunks: NotRequired[List[Dict[str, Any]]]
    
    # Context synthesis
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
    errors: NotRequired[List[Dict[str, Any]]]
    retry_count: NotRequired[int]
    
    # Knowledge base
    kb_update_data: NotRequired[Dict[str, Any]]
    
    # Control flow
    next_action: NotRequired[str]  # for conditional routing
    human_review_required: NotRequired[bool]
    human_review_result: NotRequired[str]  # "approved", "rejected", "revision"


# ============================================================================
# Node Implementations
# ============================================================================

class RIAWorkflow:
    """RIA Impact Assessment workflow using LangGraph."""
    
    # Belgian RIA 21 Impact Themes with keywords (from Belgian RIA form)
    BELGIAN_IMPACT_THEMES = {
        1: {
            "name": "Lutte contre la pauvreté / Combating poverty",
            "keywords": "Revenu minimum conforme à la dignité humaine, accès à des services de qualité, surendettement, risque de pauvreté ou d'exclusion sociale (y compris chez les mineurs), illettrisme, fracture numérique"
        },
        2: {
            "name": "Égalité des chances et cohésion sociale / Equal opportunities and social cohesion",
            "keywords": "Non-discrimination, égalité de traitement, accès aux biens et services, accès à l'information, à l'éducation et à la formation, écart de revenu, effectivité des droits civils, politiques et sociaux (en particulier pour les populations fragilisées, les enfants, les personnes âgées, les personnes handicapées et les minorités)"
        },
        3: {
            "name": "Égalité des femmes et les hommes / Equality between women and men",
            "keywords": "Accès des femmes et des hommes aux ressources: revenus, travail, responsabilités, santé/soins/bien-être, sécurité, éducation/savoir/formation, mobilité, temps, loisirs, etc. Exercice des droits fondamentaux par les femmes et les hommes droits civils, sociaux et politiques"
        },
        4: {
            "name": "Santé / Health",
            "keywords": "Accès aux soins de santé de qualité, efficacité de l'offre de soins, espérance de vie en bonne santé, traitements des maladies chroniques (maladies cardiovasculaires, cancers, diabètes et maladies respiratoires chroniques), déterminants de la santé (niveau socio-économique, alimentation, pollution), qualité de la vie"
        },
        5: {
            "name": "Emploi / Employment",
            "keywords": "Accès au marché de l'emploi, emplois de qualité, chômage, travail au noir, conditions de travail et de licenciement, carrière, temps de travail, bien-être au travail, accidents de travail, maladies professionnelles, équilibre vie privée - vie professionnelle, rémunération convenable, possibilités de formation professionnelle, relations collectives de travail"
        },
        6: {
            "name": "Modes de consommation et production / Consumption and production patterns",
            "keywords": "Stabilité/prévisibilité des prix, information et protection du consommateur, utilisation efficace des ressources, évaluation et intégration des externalités (environnementales et sociales) tout au long du cycle de vie des produits et services, modes de gestion des organisations"
        },
        7: {
            "name": "Développement économique / Economic development",
            "keywords": "Création d'entreprises, production de biens et de services, productivité du travail et des ressources/matières premières, facteurs de compétitivité, accès au marché et à la profession, transparence du marché, accès aux marchés publics, relations commerciales et financières internationales, balance des importations/exportations, économie souterraine, sécurité d'approvisionnement des ressources énergétiques, minérales et organiques"
        },
        8: {
            "name": "Investissements / Investments",
            "keywords": "Investissements en capital physique (machines, véhicules, infrastructures), technologique, intellectuel (logiciel, recherche et développement) et humain, niveau d'investissement net en pourcentage du PIB"
        },
        9: {
            "name": "Recherche et développement / Research and development",
            "keywords": "Opportunités de recherche et développement, innovation par l'introduction et la diffusion de nouveaux modes de production, de nouvelles pratiques d'entreprises ou de nouveaux produits et services, dépenses de recherche et de développement"
        },
        10: {
            "name": "PME / SMEs",
            "keywords": "Impact sur le développement des PME"
        },
        11: {
            "name": "Charges administratives / Administrative burdens",
            "keywords": "Réduction des formalités et des obligations administratives liées directement ou indirectement à l'exécution, au respect et/ou au maintien d'un droit, d'une interdiction ou d'une obligation"
        },
        12: {
            "name": "Énergie / Energy",
            "keywords": "Mix énergétique (bas carbone, renouvelable, fossile), utilisation de la biomasse (bois, biocarburants), efficacité énergétique, consommation d'énergie de l'industrie, des services, des transports et des ménages, sécurité d'approvisionnement, accès aux biens et services énergétiques"
        },
        13: {
            "name": "Mobilité / Mobility",
            "keywords": "Volume de transport (nombre de kilomètres parcourus et nombre de véhicules), offre de transports collectifs, offre routière, ferroviaire, maritime et fluviale pour les transports de marchandises, répartitions des modes de transport (modal shift), sécurité, densité du trafic"
        },
        14: {
            "name": "Alimentation / Food",
            "keywords": "Accès à une alimentation sûre (contrôle de qualité), alimentation saine et à haute valeur nutritionnelle, gaspillages, commerce équitable"
        },
        15: {
            "name": "Changements climatiques / Climate change",
            "keywords": "Émissions de gaz à effet de serre, capacité d'adaptation aux effets des changements climatiques, résilience, transition énergétique, sources d'énergies renouvelables, utilisation rationnelle de l'énergie, efficacité énergétique, performance énergétique des bâtiments, piégeage du carbone"
        },
        16: {
            "name": "Ressources naturelles / Natural resources",
            "keywords": "Gestion efficiente des ressources, recyclage, réutilisation, qualité et consommation de l'eau (eaux de surface et souterraines, mers et océans), qualité et utilisation du sol (pollution, teneur en matières organiques, érosion, assèchement, inondations, densification, fragmentation), déforestation"
        },
        17: {
            "name": "Air intérieur et extérieur / Outdoor and indoor air",
            "keywords": "Qualité de l'air (y compris l'air intérieur), émissions de polluants (agents chimiques ou biologiques méthane, hydrocarbures, solvants, SOX, NOx, NH3), particules fines"
        },
        18: {
            "name": "Biodiversité / Biodiversity",
            "keywords": "Niveaux de la diversité biologique, état des écosystèmes (restauration, conservation, valorisation, zones protégées), altération et fragmentation des habitats, biotechnologies, brevets d'invention sur la matière biologique, utilisation des ressources génétiques, services rendus par les écosystèmes (purification de l'eau et de l'air, ...), espèces domestiquées ou cultivées, espèces exotiques envahissantes, espèces menacées"
        },
        19: {
            "name": "Nuisances / Nuisance",
            "keywords": "Nuisances sonores, visuelles ou olfactives, vibrations, rayonnements ionisants, non ionisants et électromagnétiques, nuisances lumineuses"
        },
        20: {
            "name": "Autorités publiques / Government",
            "keywords": "Fonctionnement démocratique des organes de concertation et consultation, services publics aux usagers, plaintes, recours, contestations, mesures d'exécution, investissements publics"
        },
        21: {
            "name": "Cohérence des politiques en faveur du développement / Policy coherence for development",
            "keywords": "Prise en considération des impacts involontaires des mesures politiques belges sur les intérêts des pays en voie de développement"
        }
    }
    
    # EU domain to Belgian category mapping (for context retrieval)
    EU_DOMAIN_TO_BELGIAN_CATEGORY = {
        "Environment": [15, 16, 17, 18, 19],  # Climate, Natural resources, Air, Biodiversity, Nuisance
        "Health": [4],  # Health
        "Digital": [2, 3, 5],  # Social cohesion, Equality, Employment
        "Competition": [6, 7, 10],  # Consumption, Economic development, SMEs
        "Employment": [5],  # Employment
        "Energy": [12, 15],  # Energy, Climate change
        "Transport": [13],  # Mobility
        "Agriculture": [14, 16, 18],  # Food, Natural resources, Biodiversity
        "Social": [1, 2, 3, 4],  # Poverty, Social cohesion, Equality, Health
        "Economic": [5, 6, 7, 8, 9, 10],  # Employment, Consumption, Economic dev, Investments, R&D, SMEs
        "Administrative": [11, 20],  # Administrative burdens, Government
        "International": [21]  # Policy coherence for development
    }
    
    # Category keywords for graph retrieval
    CATEGORY_KEYWORDS = {
        "Environment": ["environment", "climate", "biodiversity", "nature", "ecosystem", "green"],
        "Health": ["health", "medical", "disease", "patient", "healthcare", "hospital"],
        "Digital": ["digital", "data", "cyber", "ai", "algorithm", "technology", "online"],
        "Competition": ["competition", "market", "antitrust", "monopoly", "cartel"],
        "Employment": ["employment", "labour", "worker", "job", "workplace", "employee"],
        "Energy": ["energy", "renewable", "solar", "wind", "power", "electricity"],
        "Transport": ["transport", "mobility", "vehicle", "traffic", "infrastructure"],
        "Agriculture": ["agriculture", "farming", "crop", "livestock", "rural"]
    }
    
    def __init__(
        self,
        vector_store_path: str = "vector_store",
        knowledge_graph_path: str = "knowledge_graph.pkl"
    ):
        """Initialize workflow with vector store and knowledge graph."""
        if not LANGGRAPH_AVAILABLE:
            raise RuntimeError("LangGraph is not installed. Install with: pip install langgraph")
        
        # Load vector store
        self.vector_store = None
        if Path(vector_store_path).exists():
            try:
                self.vector_store = VectorStore(use_local_model=True)
                self.vector_store.load(vector_store_path)
                print(f"✅ Vector store loaded from: {vector_store_path}")
            except Exception as e:
                print(f"⚠️  Could not load vector store: {e}")
        
        # Load knowledge graph
        self.knowledge_graph = None
        if Path(knowledge_graph_path).exists():
            try:
                builder = KnowledgeGraphBuilder()
                self.knowledge_graph = builder.load_graph(knowledge_graph_path)
                print(f"✅ Knowledge graph loaded from: {knowledge_graph_path}")
            except Exception as e:
                print(f"⚠️  Could not load knowledge graph: {e}")
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(RIAState)
        
        # Add nodes
        workflow.add_node("ingest_proposal", self.ingest_proposal)
        workflow.add_node("extract_features", self.extract_features)
        workflow.add_node("route_retrieval", self.route_retrieval_strategy)
        workflow.add_node("retrieve_vector", self.retrieve_from_vector_store)
        workflow.add_node("retrieve_graph", self.retrieve_from_knowledge_graph)
        workflow.add_node("merge_results", self.merge_retrieval_results)
        workflow.add_node("check_retrieval_quality", self.check_retrieval_quality)
        workflow.add_node("expand_retrieval", self.expand_retrieval)
        workflow.add_node("synthesize_context", self.synthesize_context)
        workflow.add_node("validate_context", self.validate_context_quality)
        workflow.add_node("council_stage1", self.council_stage1_generate)
        workflow.add_node("council_stage2", self.council_stage2_rankings)
        workflow.add_node("council_stage3", self.council_stage3_synthesize)
        workflow.add_node("validate_council", self.validate_council_output)
        workflow.add_node("refine_council", self.refine_council_output)
        workflow.add_node("extract_sections", self.extract_ria_sections)
        workflow.add_node("structure_assessment", self.structure_assessment)
        workflow.add_node("calculate_quality", self.calculate_quality_metrics)
        workflow.add_node("route_review", self.route_to_human_review)
        workflow.add_node("human_review", self.human_review_checkpoint)
        workflow.add_node("generate_report", self.generate_report_output)
        workflow.add_node("prepare_kb_update", self.prepare_knowledge_base_update)
        workflow.add_node("update_vector", self.update_vector_store)
        workflow.add_node("update_graph", self.update_knowledge_graph)
        workflow.add_node("log_error", self.log_error)
        
        # Set entry point
        workflow.set_entry_point("ingest_proposal")
        
        # Add edges
        workflow.add_edge("ingest_proposal", "extract_features")
        workflow.add_edge("extract_features", "route_retrieval")
        
        # Conditional routing from route_retrieval
        workflow.add_conditional_edges(
            "route_retrieval",
            self.route_retrieval_decision,
            {
                "vector_only": "retrieve_vector",
                "graph_only": "retrieve_graph",
                "hybrid": "retrieve_vector",  # Start with vector, then graph
                "graph_first": "retrieve_graph"
            }
        )
        
        # After vector retrieval in hybrid mode, also retrieve from graph
        workflow.add_conditional_edges(
            "retrieve_vector",
            self.should_retrieve_graph,
            {
                "yes": "retrieve_graph",
                "no": "merge_results"
            }
        )
        
        # After graph retrieval, go to merge
        workflow.add_edge("retrieve_graph", "merge_results")
        
        # After merge, check quality
        workflow.add_edge("merge_results", "check_retrieval_quality")
        
        # Always proceed after quality check (no retries to avoid loops)
        workflow.add_edge("check_retrieval_quality", "synthesize_context")
        
        # After synthesis, go directly to council (no validation loop)
        workflow.add_edge("synthesize_context", "council_stage1")
        
        # Council stages (sequential) - validate after stage 3
        workflow.add_edge("council_stage1", "council_stage2")
        workflow.add_edge("council_stage2", "council_stage3")
        workflow.add_edge("council_stage3", "validate_council")
        
        # Conditional routing from validation - refine if needed, otherwise proceed
        workflow.add_conditional_edges(
            "validate_council",
            self.council_validation_decision,
            {
                "proceed": "extract_sections",
                "refine": "refine_council"
            }
        )
        
        # Refinement loops back to council_stage3 (with retry limit)
        workflow.add_edge("refine_council", "council_stage3")
        
        # Structure assessment
        workflow.add_edge("extract_sections", "structure_assessment")
        workflow.add_edge("structure_assessment", "calculate_quality")
        workflow.add_edge("calculate_quality", "route_review")
        
        # Conditional routing for human review
        workflow.add_conditional_edges(
            "route_review",
            self.review_decision,
            {
                "review": "human_review",
                "approve": "generate_report"
            }
        )
        
        # Human review conditional routing - simplified to avoid loops
        workflow.add_conditional_edges(
            "human_review",
            self.human_review_decision,
            {
                "approved": "generate_report",
                "rejected": END,
                "revision": "extract_sections"  # Don't loop back to council, just proceed
            }
        )
        
        # After report generation
        workflow.add_edge("generate_report", "prepare_kb_update")
        workflow.add_edge("prepare_kb_update", "update_vector")
        workflow.add_edge("update_vector", "update_graph")
        workflow.add_edge("update_graph", END)
        
        return workflow.compile()
    
    # ========================================================================
    # Node Functions
    # ========================================================================
    
    def ingest_proposal(self, state: RIAState) -> RIAState:
        """Ingest and validate proposal input."""
        print(f"\n📥 Ingesting proposal...")
        
        proposal = state.get("proposal", "")
        if not proposal:
            return self._add_error(state, "No proposal provided")
        
        # Initialize state
        new_state = {
            **state,
            "context": state.get("context", {}),
            "errors": [],
            "retry_count": 0,
            "quality_metrics": {}
        }
        
        print(f"✅ Proposal ingested: {proposal[:100]}...")
        return new_state
    
    def extract_features(self, state: RIAState) -> RIAState:
        """Extract features from proposal for routing decisions."""
        print(f"\n🔍 Extracting proposal features...")
        
        proposal = state.get("proposal", "").lower()
        context = state.get("context", {})
        
        # Extract categories
        detected_categories = []
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in proposal for kw in keywords):
                detected_categories.append(category)
        
        # Estimate complexity (simple heuristic)
        word_count = len(state.get("proposal", "").split())
        complexity = "simple" if word_count < 200 else "complex" if word_count > 500 else "medium"
        
        # Extract metadata
        features = {
            "categories": detected_categories,
            "complexity": complexity,
            "word_count": word_count,
            "has_metadata": bool(context),
            "jurisdiction": context.get("jurisdiction", "unknown"),
            "category": context.get("category") or (detected_categories[0] if detected_categories else None)
        }
        
        print(f"✅ Features extracted: {len(detected_categories)} categories, {complexity} complexity")
        
        return {**state, "features": features}
    
    def route_retrieval_strategy(self, state: RIAState) -> RIAState:
        """Determine retrieval strategy based on features."""
        print(f"\n🧭 Routing retrieval strategy...")
        
        features = state.get("features", {})
        context = state.get("context", {})
        
        # Strategy decision logic
        strategy = "hybrid"  # default
        
        # If user specified strategy in context, use it
        if "retrieval_strategy" in context:
            strategy = context["retrieval_strategy"]
        # If strong category match, use graph-first
        elif features.get("categories") and len(features["categories"]) > 0:
            strategy = "graph_first"
        # If simple proposal, use vector-only
        elif features.get("complexity") == "simple":
            strategy = "vector_only"
        # If complex, use hybrid
        elif features.get("complexity") == "complex":
            strategy = "hybrid"
        
        print(f"✅ Strategy selected: {strategy}")
        
        return {**state, "retrieval_strategy": strategy}
    
    def route_retrieval_decision(self, state: RIAState) -> str:
        """Decision function for retrieval routing."""
        strategy = state.get("retrieval_strategy", "hybrid")
        return strategy
    
    def should_retrieve_graph(self, state: RIAState) -> str:
        """Decision function: should we also retrieve from graph after vector?"""
        strategy = state.get("retrieval_strategy", "hybrid")
        # Check if we already have graph results (from graph_first path)
        graph_results = state.get("graph_results", [])
        # If hybrid and no graph results yet, retrieve from graph
        if strategy == "hybrid" and not graph_results:
            return "yes"
        return "no"
    
    def should_continue_retry(self, state: RIAState) -> str:
        """Decision function: should we continue retrying or proceed?"""
        retry_count = state.get("retry_count", 0)
        # If we've retried too much, just proceed
        if retry_count >= 3:
            return "proceed"
        return "retry"
    
    def retrieve_from_vector_store(self, state: RIAState) -> RIAState:
        """Retrieve chunks from vector store."""
        print(f"\n🔎 Retrieving from vector store...")
        
        if not self.vector_store:
            return self._add_error(state, "Vector store not available")
        
        proposal = state.get("proposal", "")
        context = state.get("context", {})
        strategy = state.get("retrieval_strategy", "hybrid")
        top_k = 20
        
        # Build metadata filters (optional - don't filter too strictly)
        filters = None  # Don't filter by default to get more results
        # Only filter if explicitly requested
        if context and context.get("strict_filtering", False):
            filters = {}
            if "jurisdiction" in context:
                filters["jurisdiction"] = context["jurisdiction"]
            if "category" in context:
                filters["categories"] = context["category"]
            if "year" in context:
                filters["year"] = context["year"]
        
        try:
            # Determine search parameters based on strategy
            if strategy in ["dense", "hybrid"]:
                dense_weight = 1.0 if strategy == "dense" else 0.7
                sparse_weight = 0.0 if strategy == "dense" else 0.3
                
                results = self.vector_store.search(
                    proposal,
                    top_k=top_k,
                    filter_metadata=filters,
                    use_hybrid=(strategy == "hybrid"),
                    dense_weight=dense_weight,
                    sparse_weight=sparse_weight
                )
            elif strategy == "sparse":
                results = self.vector_store.search(
                    proposal,
                    top_k=top_k,
                    filter_metadata=filters if filters else None,
                    use_hybrid=False,
                    dense_weight=0.0,
                    sparse_weight=1.0
                )
            else:
                results = []
            
            print(f"✅ Retrieved {len(results)} chunks from vector store")
            
            return {**state, "vector_results": results}
        
        except Exception as e:
            return self._add_error(state, f"Vector store retrieval error: {str(e)}")
    
    def retrieve_from_knowledge_graph(self, state: RIAState) -> RIAState:
        """Retrieve chunks from knowledge graph."""
        print(f"\n🕸️  Retrieving from knowledge graph...")
        
        if not self.knowledge_graph:
            return self._add_error(state, "Knowledge graph not available")
        
        proposal = state.get("proposal", "").lower()
        features = state.get("features", {})
        top_k = 10
        
        try:
            # Get categories from features or extract from proposal
            categories = features.get("categories", [])
            if not categories:
                # Extract categories from proposal
                for category, keywords in self.CATEGORY_KEYWORDS.items():
                    if any(kw in proposal for kw in keywords):
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
            
            # Limit results
            chunks = chunks[:top_k]
            
            print(f"✅ Retrieved {len(chunks)} chunks from knowledge graph")
            
            return {**state, "graph_results": chunks}
        
        except Exception as e:
            return self._add_error(state, f"Knowledge graph retrieval error: {str(e)}")
    
    def merge_retrieval_results(self, state: RIAState) -> RIAState:
        """Merge and deduplicate retrieval results."""
        print(f"\n🔀 Merging retrieval results...")
        
        vector_results = state.get("vector_results", [])
        graph_results = state.get("graph_results", [])
        
        # Combine results
        all_chunks = vector_results + graph_results
        
        # Deduplicate by chunk_id
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            chunk_id = chunk.get("chunk_id", "")
            if chunk_id and chunk_id not in seen:
                seen.add(chunk_id)
                unique_chunks.append(chunk)
        
        # Re-rank by score
        unique_chunks = sorted(
            unique_chunks,
            key=lambda x: x.get("score", 0),
            reverse=True
        )[:20]  # Top 20
        
        print(f"✅ Merged to {len(unique_chunks)} unique chunks")
        
        return {**state, "merged_chunks": unique_chunks}
    
    def check_retrieval_quality(self, state: RIAState) -> RIAState:
        """Check quality of retrieval results."""
        print(f"\n📊 Checking retrieval quality...")
        
        chunks = state.get("merged_chunks", [])
        retry_count = state.get("retry_count", 0)
        
        # Quality metrics
        chunk_count = len(chunks)
        avg_score = sum(c.get("score", 0) for c in chunks) / chunk_count if chunk_count > 0 else 0
        
        # Quality thresholds
        min_chunks = 5
        min_score = 0.3
        
        quality_ok = chunk_count >= min_chunks and avg_score >= min_score
        
        quality_metrics = state.get("quality_metrics", {})
        quality_metrics["retrieval"] = {
            "chunk_count": chunk_count,
            "avg_score": avg_score,
            "quality_ok": quality_ok
        }
        
        print(f"✅ Quality check: {chunk_count} chunks, avg score {avg_score:.3f}")
        
        return {**state, "quality_metrics": quality_metrics}
    
    def retrieval_quality_decision(self, state: RIAState) -> str:
        """Decision function for retrieval quality."""
        quality_metrics = state.get("quality_metrics", {})
        retrieval_quality = quality_metrics.get("retrieval", {})
        retry_count = state.get("retry_count", 0)
        chunks = state.get("merged_chunks", [])
        
        # Always proceed if we have some chunks, or if we've retried too much
        if len(chunks) > 0 or retry_count >= 2:
            return "proceed"
        # Only expand if we have no chunks and haven't retried
        if len(chunks) == 0 and retry_count < 2:
            return "expand"
        return "proceed"
    
    def expand_retrieval(self, state: RIAState) -> RIAState:
        """Expand retrieval with more permissive parameters."""
        print(f"\n🔄 Expanding retrieval...")
        
        retry_count = state.get("retry_count", 0) + 1
        
        # If we've retried too much, just proceed with what we have
        if retry_count >= 3:
            print(f"⚠️  Max retries reached ({retry_count}), proceeding with available results")
            return {**state, "retry_count": retry_count}
        
        strategy = state.get("retrieval_strategy", "hybrid")
        
        # Switch to hybrid if not already
        if strategy != "hybrid":
            strategy = "hybrid"
        
        print(f"✅ Expanded retrieval (attempt {retry_count})")
        
        return {
            **state,
            "retrieval_strategy": strategy,
            "retry_count": retry_count,
            "vector_results": [],  # Clear previous results
            "graph_results": []
        }
    
    def synthesize_context(self, state: RIAState) -> RIAState:
        """Synthesize retrieved context into coherent, structured text with substantial content."""
        print(f"\n📝 Synthesizing context...")
        
        chunks = state.get("merged_chunks", [])
        proposal = state.get("proposal", "")
        
        if not chunks:
            synthesized = "No relevant context found."
        else:
            # Sort chunks by score (highest first) to prioritize most relevant
            sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
            
            # Group chunks by analysis type and jurisdiction
            eu_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("jurisdiction") == "EU"]
            belgian_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("jurisdiction") == "Belgian"]
            other_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("jurisdiction") not in ["EU", "Belgian"]]
            
            # Group by analysis type
            problem_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("analysis_type", "").startswith("problem")]
            option_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("analysis_type", "").startswith("option")]
            impact_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("analysis_type", "").startswith("impact")]
            evidence_chunks = [c for c in sorted_chunks if c.get("metadata", {}).get("analysis_type", "").startswith("evidence")]
            category_chunks = [c for c in sorted_chunks if "category" in c.get("chunk_id", "").lower() or c.get("metadata", {}).get("chunk_type") == "category"]
            
            synthesized = f"""RELEVANT CONTEXT FOR IMPACT ASSESSMENT

Proposal to Assess: {proposal}

================================================================================
EU IMPACT ASSESSMENT DOCUMENTS (Reference Examples)
================================================================================
"""
            
            # Process EU chunks with document references
            seen_docs = set()
            eu_docs = {}
            for chunk in eu_chunks[:15]:  # Top 15 EU chunks
                metadata = chunk.get("metadata", {})
                doc_ref = metadata.get("swd_reference") or metadata.get("com_reference") or metadata.get("source_document", "Unknown")
                doc_key = doc_ref
                
                if doc_key not in seen_docs:
                    seen_docs.add(doc_key)
                    eu_docs[doc_key] = {
                        "reference": doc_ref,
                        "domain": metadata.get("policy_domain", "N/A"),
                        "year": metadata.get("year", "N/A"),
                        "lead_dg": metadata.get("lead_dg", "N/A"),
                        "chunks": []
                    }
                
                analysis_type = metadata.get("analysis_type", "general")
                content = chunk.get("content", "").strip()
                
                # Include more substantial content (up to 800 chars, try to end at sentence)
                if len(content) > 800:
                    truncated = content[:800]
                    last_period = truncated.rfind('.')
                    last_newline = truncated.rfind('\n')
                    cut_point = max(last_period, last_newline) if last_period > 600 or last_newline > 600 else 800
                    content = content[:cut_point] + ("..." if cut_point < len(content) else "")
                
                eu_docs[doc_key]["chunks"].append({
                    "type": analysis_type,
                    "content": content,
                    "score": chunk.get("score", 0)
                })
            
            # Format EU documents
            for doc_key, doc_info in list(eu_docs.items())[:5]:  # Top 5 EU documents
                synthesized += f"\nDocument: {doc_info['reference']}\n"
                synthesized += f"Policy Domain: {doc_info['domain']} | Year: {doc_info['year']} | Lead DG: {doc_info['lead_dg']}\n"
                synthesized += "-" * 80 + "\n"
                
                # Group chunks by type within document
                for chunk_info in sorted(doc_info["chunks"], key=lambda x: x["score"], reverse=True)[:3]:
                    analysis_type = chunk_info["type"].replace("_", " ").title() if chunk_info["type"] else "Analysis"
                    synthesized += f"\n[{analysis_type}]\n"
                    synthesized += f"{chunk_info['content']}\n\n"
            
            # Belgian RIA examples
            if belgian_chunks:
                synthesized += "\n" + "=" * 80 + "\n"
                synthesized += "BELGIAN RIA DOCUMENTS (Reference Examples)\n"
                synthesized += "=" * 80 + "\n"
                
                seen_belgian_docs = set()
                for chunk in belgian_chunks[:10]:  # Top 10 Belgian chunks
                    metadata = chunk.get("metadata", {})
                    doc_id = metadata.get("document_id") or metadata.get("source_document", "Unknown")
                    
                    if doc_id not in seen_belgian_docs:
                        seen_belgian_docs.add(doc_id)
                        content = chunk.get("content", "").strip()
                        
                        if len(content) > 600:
                            truncated = content[:600]
                            last_period = truncated.rfind('.')
                            content = content[:last_period + 1] if last_period > 400 else content[:600] + "..."
                        
                        category = metadata.get("category", "N/A")
                        year = metadata.get("year", "N/A")
                        
                        synthesized += f"\nBelgian RIA Document: {doc_id} | Category: {category} | Year: {year}\n"
                        synthesized += "-" * 80 + "\n"
                        synthesized += f"{content}\n\n"
            
            # Analysis patterns by type
            synthesized += "\n" + "=" * 80 + "\n"
            synthesized += "ANALYSIS PATTERNS AND METHODOLOGIES\n"
            synthesized += "=" * 80 + "\n"
            
            # Problem definition examples
            if problem_chunks:
                synthesized += "\n[Problem Definition Patterns]\n"
                for chunk in problem_chunks[:3]:
                    content = chunk.get("content", "").strip()
                    if len(content) > 500:
                        content = content[:500] + "..."
                    metadata = chunk.get("metadata", {})
                    doc_ref = metadata.get("swd_reference") or metadata.get("source_document", "Unknown")
                    synthesized += f"From: {doc_ref}\n{content}\n\n"
            
            # Policy option examples
            if option_chunks:
                synthesized += "\n[Policy Option Analysis Patterns]\n"
                for chunk in option_chunks[:3]:
                    content = chunk.get("content", "").strip()
                    if len(content) > 500:
                        content = content[:500] + "..."
                    metadata = chunk.get("metadata", {})
                    doc_ref = metadata.get("swd_reference") or metadata.get("source_document", "Unknown")
                    synthesized += f"From: {doc_ref}\n{content}\n\n"
            
            # Impact assessment examples
            if impact_chunks:
                synthesized += "\n[Impact Assessment Patterns]\n"
                for chunk in impact_chunks[:3]:
                    content = chunk.get("content", "").strip()
                    if len(content) > 500:
                        content = content[:500] + "..."
                    metadata = chunk.get("metadata", {})
                    doc_ref = metadata.get("swd_reference") or metadata.get("source_document", "Unknown")
                    synthesized += f"From: {doc_ref}\n{content}\n\n"
            
            # Supporting evidence
            if evidence_chunks:
                synthesized += "\n[Supporting Evidence and Data]\n"
                for chunk in evidence_chunks[:5]:
                    content = chunk.get("content", "").strip()
                    if len(content) > 400:
                        content = content[:400] + "..."
                    metadata = chunk.get("metadata", {})
                    doc_ref = metadata.get("swd_reference") or metadata.get("source_document", "Unknown")
                    synthesized += f"From: {doc_ref}\n{content}\n\n"
            
            # Policy categories mapping
            if category_chunks:
                synthesized += "\n" + "=" * 80 + "\n"
                synthesized += "RELEVANT POLICY CATEGORIES\n"
                synthesized += "=" * 80 + "\n"
                categories = set()
                for chunk in category_chunks:
                    metadata = chunk.get("metadata", {})
                    cats = metadata.get("categories", [])
                    if isinstance(cats, list):
                        categories.update(cats)
                    elif isinstance(cats, str):
                        categories.add(cats)
                    cat = metadata.get("category")
                    if cat:
                        categories.add(cat)
                
                for cat in sorted(categories)[:10]:
                    synthesized += f"- {cat}\n"
            
            synthesized += "\n" + "=" * 80 + "\n"
            synthesized += "INSTRUCTIONS FOR ASSESSMENT GENERATION\n"
            synthesized += "=" * 80 + "\n"
            synthesized += """
Use the above EU Impact Assessment documents and Belgian RIA examples as reference for:
1. Analysis depth and structure (EU-style detailed, evidence-based analysis)
2. Problem definition approaches
3. Policy option evaluation methodologies
4. Impact assessment patterns and frameworks
5. Evidence integration and citation styles

Map EU domain knowledge (from EU documents) to Belgian RIA categories (21 impact themes).
Reference specific documents and analysis patterns where relevant in your assessment.
"""
        
        print(f"✅ Context synthesized ({len(synthesized)} chars, {len(chunks)} chunks processed)")
        
        return {**state, "synthesized_context": synthesized}
    
    def validate_context_quality(self, state: RIAState) -> RIAState:
        """Validate synthesized context quality."""
        print(f"\n✅ Validating context quality...")
        
        synthesized = state.get("synthesized_context", "")
        chunks = state.get("merged_chunks", [])
        
        # Simple validation: check if context is substantial
        is_valid = len(synthesized) > 100 and len(chunks) >= 3
        
        quality_metrics = state.get("quality_metrics", {})
        quality_metrics["context"] = {
            "length": len(synthesized),
            "chunk_count": len(chunks),
            "is_valid": is_valid
        }
        
        print(f"✅ Context validation: {'PASS' if is_valid else 'FAIL'}")
        
        return {**state, "quality_metrics": quality_metrics}
    
    def context_validation_decision(self, state: RIAState) -> str:
        """Decision function for context validation."""
        quality_metrics = state.get("quality_metrics", {})
        context_quality = quality_metrics.get("context", {})
        retry_count = state.get("retry_count", 0)
        synthesized = state.get("synthesized_context", "")
        
        # Always proceed if we have context, or if we've retried too much
        if len(synthesized) > 50 or retry_count >= 2:
            return "proceed"
        # Only retry if we have no context and haven't retried much
        if len(synthesized) <= 50 and retry_count < 2:
            return "retry"
        return "proceed"
    
    async def council_stage1_generate(self, state: RIAState) -> RIAState:
        """Generate initial opinions from council models."""
        print(f"\n🤖 Council Stage 1: Generating opinions...")
        
        proposal = state.get("proposal", "")
        synthesized = state.get("synthesized_context", "")
        
        # Create enhanced query for Belgian RIA with EU analysis style
        themes_list = []
        for theme_num, theme_info in self.BELGIAN_IMPACT_THEMES.items():
            themes_list.append(f"[{theme_num}] {theme_info['name']}")
        
        enhanced_query = f"""Generate a comprehensive Belgian Regulatory Impact Assessment (RIA) for the following regulatory proposal:

{proposal}

Relevant Context (from EU and Belgian RIA documents):
{synthesized}

CRITICAL: Generate a BELGIAN RIA that:
- Uses Belgian RIA structure with all 21 impact themes
- Uses EU-style detailed, evidence-based analysis
- Maps EU domain knowledge to Belgian categories
- Includes citations when referencing retrieved documents (e.g., "SWD(2022) 167 final", "COM(2022) 304 final", "Belgian RIA 2014A03330.002")

21 Impact Themes to Assess:
{chr(10).join(themes_list)}

REQUIRED STRUCTURE (in this order):
1. Background and Problem Definition (MOST IMPORTANT - define the problem clearly, drawing on similar problem definitions from retrieved EU documents. Cite sources like "SWD(2022) 167 final" when referencing their problem definition approaches.)
2. Executive Summary
3. Proposal Overview
4. 21 Impact Themes Assessment (with citations where referencing analysis patterns or methodologies from retrieved documents)
5. Overall Assessment Summary
6. Recommendations

For each theme, provide: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT] with detailed EU-style explanation and citations where appropriate."""
        
        try:
            # Pass context for specialized roles
            stage1_results = await stage1_collect_responses(
                enhanced_query,
                context=synthesized,
                specialized_roles=True
            )
            if stage1_results:
                print(f"✅ Stage 1 complete: {len(stage1_results)} opinions")
                return {**state, "stage1_results": stage1_results}
            else:
                raise Exception("No results from council")
        except Exception as e:
            print(f"⚠️  Council Stage 1 failed (likely no OpenRouter key): {str(e)[:100]}")
            print("   Using OpenAI directly as fallback...")
            # Fallback to OpenAI directly - this will populate stage1, stage2, and stage3
            return await self._openai_fallback(state, enhanced_query)
    
    async def council_stage2_rankings(self, state: RIAState) -> RIAState:
        """Collect rankings from council models."""
        print(f"\n🤖 Council Stage 2: Collecting rankings...")
        
        proposal = state.get("proposal", "")
        stage1_results = state.get("stage1_results", [])
        
        if not stage1_results:
            print("⚠️  No Stage 1 results - skipping Stage 2, will use Stage 1 fallback result")
            # Create empty stage2 for compatibility
            return {**state, "stage2_results": []}
        
        try:
            enhanced_query = f"""Evaluate the following Belgian RIA assessments for the regulatory proposal:

{proposal}

Please evaluate the responses based on:
- Accuracy and adherence to Belgian RIA structure (21 themes)
- Completeness of EU-style detailed analysis
- Quality of evidence-based reasoning
- Proper mapping of EU domains to Belgian categories"""
            
            # Pass context for RIA-specific evaluation
            stage2_results, label_to_model = await stage2_collect_rankings(
                enhanced_query,
                stage1_results,
                context=synthesized
            )
            
            print(f"✅ Stage 2 complete: {len(stage2_results)} rankings")
            
            return {**state, "stage2_results": stage2_results}
        
        except Exception as e:
            return self._add_error(state, f"Council Stage 2 error: {str(e)}")
    
    async def council_stage3_synthesize(self, state: RIAState) -> RIAState:
        """Synthesize final assessment using Meta-Chairman."""
        print(f"\n🤖 Council Stage 3: Meta-Chairman synthesis...")
        
        proposal = state.get("proposal", "")
        synthesized = state.get("synthesized_context", "")
        stage1_results = state.get("stage1_results", [])
        stage2_results = state.get("stage2_results", [])
        
        # If no council results, use OpenAI fallback
        if not stage1_results:
            print("⚠️  No council results - using OpenAI fallback for Stage 3")
            themes_list = "\n".join([f"[{n}] {info['name']}" for n, info in self.BELGIAN_IMPACT_THEMES.items()])
            enhanced_query = f"""Generate a comprehensive Belgian RIA for the following regulatory proposal:

{proposal}

Relevant Context:
{synthesized}

REQUIRED STRUCTURE:
1. Background and Problem Definition (MOST IMPORTANT - define the problem clearly, cite retrieved documents)
2. Executive Summary
3. Proposal Overview
4. 21 Impact Themes Assessment (with citations where referencing retrieved documents)
5. Overall Assessment Summary
6. Recommendations

Generate Belgian RIA structure with all 21 themes, using EU-style detailed analysis with citations:
{themes_list}"""
            return await self._openai_fallback(state, enhanced_query)
        
        try:
            themes_list = "\n".join([f"[{n}] {info['name']}" for n, info in self.BELGIAN_IMPACT_THEMES.items()])
            enhanced_query = f"""Synthesize a final Belgian RIA assessment for the regulatory proposal:

{proposal}

Ensure the synthesis:
- Follows Belgian RIA structure with all 21 themes
- Uses EU-style detailed, evidence-based analysis
- Maps EU domains to Belgian categories
- Provides clear positive/negative/no impact for each theme
- Includes Background/Problem Definition as the FIRST section (MOST IMPORTANT)
- Includes citations when referencing retrieved documents (e.g., SWD references, COM references, Belgian RIA document IDs)

REQUIRED STRUCTURE:
1. Background and Problem Definition (with citations)
2. Executive Summary
3. Proposal Overview
4. 21 Impact Themes Assessment (with citations where appropriate)
5. Overall Assessment Summary
6. Recommendations

21 Impact Themes:
{themes_list}"""
            
            # Pass context for comprehensive synthesis
            stage3_result = await stage3_synthesize_final(
                enhanced_query,
                stage1_results,
                stage2_results,
                context=synthesized
            )
            
            # Validate that we got actual content
            content = stage3_result.get("response", "")
            if not content or len(content) < 200 or "Error" in content[:100]:
                print(f"⚠️  Stage 3 returned invalid content - using OpenAI fallback")
                raise ValueError("Invalid content from Stage 3")
            
            print(f"✅ Stage 3 complete: Final synthesis generated ({len(content)} chars)")
            
            return {**state, "stage3_result": stage3_result}
        
        except Exception as e:
            print(f"⚠️  Council Stage 3 failed: {str(e)[:100]}")
            print("   Using OpenAI fallback...")
            # Fallback to OpenAI - use Stage 1 content if available, otherwise generate fresh
            themes_list = "\n".join([f"[{n}] {info['name']}" for n, info in self.BELGIAN_IMPACT_THEMES.items()])
            
            # If we have Stage 1 content, use it as context
            stage1_content = ""
            if stage1_results and len(stage1_results) > 0:
                stage1_content = stage1_results[0].get("response", "")
            
            if stage1_content and len(stage1_content) > 200:
                enhanced_query = f"""Refine and complete the following Belgian RIA assessment for the regulatory proposal:

{proposal}

Initial Assessment (to refine):
{stage1_content[:2000]}

Relevant Context:
{synthesized}

REQUIRED STRUCTURE:
1. Background and Problem Definition (MOST IMPORTANT - define the problem clearly, cite retrieved documents)
2. Executive Summary
3. Proposal Overview
4. 21 Impact Themes Assessment (with citations where referencing retrieved documents)
5. Overall Assessment Summary
6. Recommendations

Generate a complete Belgian RIA structure with all 21 themes, using EU-style detailed analysis with citations:
{themes_list}

Ensure you provide detailed assessments for ALL 21 themes with clear positive/negative/no impact determinations and include citations when referencing analysis patterns or methodologies from retrieved documents."""
            else:
                enhanced_query = f"""Generate a comprehensive Belgian RIA for the following regulatory proposal:

{proposal}

Relevant Context:
{synthesized}

REQUIRED STRUCTURE:
1. Background and Problem Definition (MOST IMPORTANT - define the problem clearly, cite retrieved documents)
2. Executive Summary
3. Proposal Overview
4. 21 Impact Themes Assessment (with citations where referencing retrieved documents)
5. Overall Assessment Summary
6. Recommendations

Generate Belgian RIA structure with all 21 themes, using EU-style detailed analysis with citations:
{themes_list}

Ensure you provide detailed assessments for ALL 21 themes with clear positive/negative/no impact determinations and include citations when referencing analysis patterns or methodologies from retrieved documents."""
            
            return await self._openai_fallback(state, enhanced_query)
    
    def validate_council_output(self, state: RIAState) -> RIAState:
        """Validate council output quality with RIA-specific criteria."""
        print(f"\n🔍 Validating council output (RIA quality checks)...")
        
        stage3_result = state.get("stage3_result", {})
        content = stage3_result.get("response", "")
        
        # RIA-specific validation checks
        validation_results = {
            "content_length": len(content),
            "has_background": False,
            "background_length": 0,
            "themes_found": 0,
            "has_citations": False,
            "citation_count": 0,
            "has_structure": False,
            "issues": []
        }
        
        # Check for Background/Problem Definition section
        background_patterns = [
            "Background and Problem Definition",
            "Background",
            "Problem Definition",
            "Problem Statement"
        ]
        for pattern in background_patterns:
            if pattern.lower() in content.lower():
                validation_results["has_background"] = True
                # Extract background section length
                idx = content.lower().find(pattern.lower())
                if idx != -1:
                    # Find next major section
                    next_sections = ["Executive Summary", "Proposal Overview", "Impact Themes", "Assessment"]
                    end_idx = len(content)
                    for section in next_sections:
                        section_idx = content.lower().find(section.lower(), idx + len(pattern))
                        if section_idx != -1 and section_idx < end_idx:
                            end_idx = section_idx
                    validation_results["background_length"] = end_idx - idx
                break
        
        # Check for all 21 impact themes (look for theme numbers [1] through [21])
        for theme_num in range(1, 22):
            theme_patterns = [
                f"[{theme_num}]",
                f"Theme {theme_num}",
                f"Impact Theme {theme_num}",
                f"#{theme_num}"
            ]
            for pattern in theme_patterns:
                if pattern in content:
                    validation_results["themes_found"] += 1
                    break
        
        # Check for citations (SWD, COM, Belgian RIA references)
        citation_patterns = [
            r"SWD\([0-9]{4}\)",
            r"COM\([0-9]{4}\)",
            r"Belgian RIA",
            r"RIA [0-9]{4}",
            r"SWD\([0-9]{4}\) [0-9]+",
        ]
        import re
        citation_count = 0
        for pattern in citation_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            citation_count += len(matches)
        validation_results["citation_count"] = citation_count
        validation_results["has_citations"] = citation_count > 0
        
        # Check for required structure sections
        required_sections = [
            "Executive Summary",
            "Proposal Overview",
            "Impact Themes",
            "Assessment Summary",
            "Recommendations"
        ]
        sections_found = sum(1 for section in required_sections if section.lower() in content.lower())
        validation_results["has_structure"] = sections_found >= 3
        
        # Determine if valid (all critical checks pass)
        is_valid = (
            len(content) > 1000 and
            validation_results["has_background"] and
            validation_results["background_length"] > 300 and
            validation_results["themes_found"] >= 15 and  # At least 15 of 21 themes
            validation_results["has_structure"]
        )
        
        # Collect issues for refinement
        if not validation_results["has_background"] or validation_results["background_length"] < 300:
            validation_results["issues"].append("Background/Problem Definition section is missing or too short")
        if validation_results["themes_found"] < 21:
            validation_results["issues"].append(f"Only {validation_results['themes_found']}/21 impact themes found")
        if not validation_results["has_citations"]:
            validation_results["issues"].append("No citations found (should reference SWD, COM, or Belgian RIA documents)")
        if not validation_results["has_structure"]:
            validation_results["issues"].append("Required structure sections are missing")
        
        validation_results["is_valid"] = is_valid
        
        quality_metrics = state.get("quality_metrics", {})
        quality_metrics["council"] = validation_results
        
        print(f"   Content length: {len(content)} chars")
        print(f"   Background section: {'✓' if validation_results['has_background'] else '✗'} ({validation_results['background_length']} chars)")
        print(f"   Impact themes: {validation_results['themes_found']}/21")
        print(f"   Citations: {validation_results['citation_count']}")
        print(f"   Structure: {'✓' if validation_results['has_structure'] else '✗'}")
        print(f"✅ Council validation: {'PASS' if is_valid else 'FAIL'}")
        if validation_results["issues"]:
            print(f"   Issues: {', '.join(validation_results['issues'])}")
        
        return {**state, "quality_metrics": quality_metrics, "validation_issues": validation_results["issues"]}
    
    def council_validation_decision(self, state: RIAState) -> str:
        """Decision function for council validation - refine if needed."""
        quality_metrics = state.get("quality_metrics", {})
        council_metrics = quality_metrics.get("council", {})
        is_valid = council_metrics.get("is_valid", False)
        
        # Check retry count to avoid infinite loops
        retry_count = state.get("council_refinement_count", 0)
        max_refinements = 2
        
        if is_valid or retry_count >= max_refinements:
            if retry_count >= max_refinements and not is_valid:
                print(f"⚠️  Max refinements reached ({max_refinements}), proceeding with current output")
            return "proceed"
        else:
            print(f"🔄 Requesting refinement (attempt {retry_count + 1}/{max_refinements})")
            return "refine"
    
    def refine_council_output(self, state: RIAState) -> RIAState:
        """Refine council output based on validation issues."""
        print(f"\n🔧 Refining council output...")
        
        # Increment retry count
        retry_count = state.get("council_refinement_count", 0)
        retry_count += 1
        
        stage3_result = state.get("stage3_result", {})
        current_content = stage3_result.get("response", "")
        validation_issues = state.get("validation_issues", [])
        proposal = state.get("proposal", "")
        synthesized = state.get("synthesized_context", "")
        
        # Build refinement prompt
        issues_text = "\n".join([f"- {issue}" for issue in validation_issues])
        
        refinement_prompt = f"""The following Belgian RIA assessment needs refinement. Please address the identified issues:

Current Assessment:
{current_content[:3000]}

Issues to Address:
{issues_text}

Original Proposal:
{proposal}

Retrieved Context:
{synthesized[:2000]}

Please refine the assessment to:
1. Ensure a comprehensive Background/Problem Definition section (minimum 500 characters) that clearly defines the problem and cites relevant EU documents
2. Assess ALL 21 impact themes with clear [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT] determinations
3. Include citations when referencing analysis patterns or methodologies from retrieved documents (e.g., "SWD(2022) 167 final", "COM(2022) 304 final", "Belgian RIA 2014A03330.002")
4. Maintain the required structure: Background/Problem Definition, Executive Summary, Proposal Overview, 21 Impact Themes Assessment, Overall Assessment Summary, Recommendations

Generate the complete refined assessment:"""
        
        # Use OpenAI for refinement (fast and reliable)
        try:
            from openai import OpenAI
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert in Belgian Regulatory Impact Assessments. Refine the provided assessment to address all identified quality issues while maintaining EU-style detailed analysis."},
                        {"role": "user", "content": refinement_prompt}
                    ],
                    temperature=0.7
                )
                
                refined_content = response.choices[0].message.content
                
                # Update stage3_result with refined content
                refined_stage3 = {
                    "model": "gpt-4-refined",
                    "response": refined_content
                }
                
                print(f"✅ Refinement complete (attempt {retry_count})")
                
                return {
                    **state,
                    "stage3_result": refined_stage3,
                    "council_refinement_count": retry_count
                }
        except Exception as e:
            print(f"⚠️  Refinement failed: {str(e)[:100]}")
            # Proceed with original content
            return {**state, "council_refinement_count": retry_count}
    
    def extract_ria_sections(self, state: RIAState) -> RIAState:
        """Extract sections from council output."""
        print(f"\n📑 Extracting RIA sections...")
        
        stage3_result = state.get("stage3_result", {})
        content = stage3_result.get("response", "")
        
        sections = {}
        
        # Note: We focus on Belgian RIA structure (21 themes) rather than EU IA sections
        # EU-style analysis is used for depth, but structure follows Belgian RIA format
        
        # Extract Background/Problem Definition section (MOST IMPORTANT - should be first)
        background_patterns = [
            r"1\.\s*Background\s+and\s+Problem\s+Definition",
            r"Background\s+and\s+Problem\s+Definition",
            r"1\.\s*Background",
            r"Background",
            r"Problem\s+Definition"
        ]
        
        background_match = None
        for pattern in background_patterns:
            background_match = re.search(pattern, content, re.IGNORECASE)
            if background_match:
                break
        
        if background_match:
            start = background_match.end()
            # Look for next section (Executive Summary, Proposal Overview, or numbered section 2)
            next_section_pattern = r"2\.\s*(Executive\s+Summary|Proposal\s+Overview|Impact\s+Themes)|Executive\s+Summary|Proposal\s+Overview"
            next_match = re.search(next_section_pattern, content[start:], re.IGNORECASE)
            end = start + (next_match.start() if next_match else min(2000, len(content) - start))
            sections["Background and Problem Definition"] = content[start:end].strip()
        else:
            sections["Background and Problem Definition"] = ""
        
        # Extract Executive Summary
        exec_summary_patterns = [
            r"2\.\s*Executive\s+Summary",
            r"Executive\s+Summary"
        ]
        exec_match = None
        for pattern in exec_summary_patterns:
            exec_match = re.search(pattern, content, re.IGNORECASE)
            if exec_match:
                break
        
        if exec_match:
            start = exec_match.end()
            next_section_pattern = r"3\.\s*(Proposal\s+Overview|Impact\s+Themes)|Proposal\s+Overview|21\s+Impact\s+Themes"
            next_match = re.search(next_section_pattern, content[start:], re.IGNORECASE)
            end = start + (next_match.start() if next_match else min(1000, len(content) - start))
            sections["Executive Summary"] = content[start:end].strip()
        else:
            sections["Executive Summary"] = ""
        
        # Extract Proposal Overview
        proposal_patterns = [
            r"3\.\s*Proposal\s+Overview",
            r"Proposal\s+Overview"
        ]
        proposal_match = None
        for pattern in proposal_patterns:
            proposal_match = re.search(pattern, content, re.IGNORECASE)
            if proposal_match:
                break
        
        if proposal_match:
            start = proposal_match.end()
            next_section_pattern = r"4\.\s*21\s+Impact\s+Themes|21\s+Impact\s+Themes"
            next_match = re.search(next_section_pattern, content[start:], re.IGNORECASE)
            end = start + (next_match.start() if next_match else min(1000, len(content) - start))
            sections["Proposal Overview"] = content[start:end].strip()
        else:
            sections["Proposal Overview"] = ""
        
        # Extract 21 Belgian impact themes assessments (using both French and English names)
        theme_assessments = {}
        for theme_num, theme_info in self.BELGIAN_IMPACT_THEMES.items():
            theme_name = theme_info["name"]
            # Try both French and English names
            french_name = theme_name.split(" / ")[0]
            english_name = theme_name.split(" / ")[1] if " / " in theme_name else theme_name
            
            # Look for theme in content (case insensitive, try both names)
            pattern_fr = rf"\b{re.escape(french_name)}\b"
            pattern_en = rf"\b{re.escape(english_name)}\b"
            pattern_num = rf"\[{theme_num}\]|Theme {theme_num}|Thème {theme_num}"
            
            match = None
            for pattern in [pattern_fr, pattern_en, pattern_num]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    break
            
            if match:
                # Extract assessment for this theme (next 200-1000 chars or until next theme)
                start = match.end()
                # Look for next theme number or end of content
                next_theme_pattern = rf"\[{theme_num + 1}\]|Theme {theme_num + 1}|Thème {theme_num + 1}"
                next_match = re.search(next_theme_pattern, content[start:start+1500], re.IGNORECASE)
                end = start + (next_match.start() if next_match else min(1000, len(content) - start))
                theme_assessments[theme_num] = {
                    "name": english_name,
                    "assessment": content[start:end].strip()
                }
            else:
                theme_assessments[theme_num] = {
                    "name": english_name,
                    "assessment": ""
                }
        
        # Format theme assessments in Belgian RIA structure
        theme_sections = []
        for theme_num in sorted(theme_assessments.keys()):
            theme_data = theme_assessments[theme_num]
            theme_name = theme_data["name"]
            assessment = theme_data["assessment"]
            keywords = self.BELGIAN_IMPACT_THEMES[theme_num]["keywords"]
            
            if assessment:
                theme_sections.append(f"[{theme_num}] {theme_name}\nKeywords: {keywords}\n\nAssessment:\n{assessment}\n")
            else:
                theme_sections.append(f"[{theme_num}] {theme_name}\nKeywords: {keywords}\n\nAssessment: Not assessed\n")
        
        sections["21 Belgian Impact Themes Assessment"] = "\n" + "="*80 + "\n".join(theme_sections)
        
        print(f"✅ Extracted {len([s for s in sections.values() if s])} sections")
        assessed_count = len([a for a in theme_assessments.values() if a.get("assessment", "")])
        print(f"✅ Extracted {assessed_count}/21 impact theme assessments")
        
        return {**state, "structured_sections": sections}
    
    def structure_assessment(self, state: RIAState) -> RIAState:
        """Structure assessment into final format."""
        print(f"\n📋 Structuring assessment...")
        
        stage3_result = state.get("stage3_result", {})
        sections = state.get("structured_sections", {})
        chunks = state.get("merged_chunks", [])
        
        # Extract sources
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
        
        structured = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": stage3_result.get("model", "unknown"),
                "retrieval_strategy": state.get("retrieval_strategy", "unknown"),
                "chunks_used": len(chunks),
                "sections": list(sections.keys())
            },
            "content": stage3_result.get("response", ""),
            "sections": sections,
            "sources": sources
        }
        
        print(f"✅ Assessment structured")
        
        return {**state, "structured_assessment": structured}
    
    def calculate_quality_metrics(self, state: RIAState) -> RIAState:
        """Calculate final quality metrics."""
        print(f"\n📊 Calculating quality metrics...")
        
        quality_metrics = state.get("quality_metrics", {})
        structured = state.get("structured_assessment", {})
        
        # Overall quality score
        sections = structured.get("sections", {})
        sections_filled = len([s for s in sections.values() if s])
        total_sections = len(sections)
        completeness = sections_filled / total_sections if total_sections > 0 else 0
        
        quality_metrics["overall"] = {
            "completeness": completeness,
            "sections_filled": sections_filled,
            "total_sections": total_sections,
            "sources_count": len(structured.get("sources", []))
        }
        
        print(f"✅ Quality metrics calculated: {completeness:.2%} complete")
        
        return {**state, "quality_metrics": quality_metrics}
    
    def route_to_human_review(self, state: RIAState) -> RIAState:
        """Route to human review if needed."""
        print(f"\n👤 Routing to human review...")
        
        quality_metrics = state.get("quality_metrics", {})
        overall = quality_metrics.get("overall", {})
        completeness = overall.get("completeness", 0)
        
        # Require review if completeness is low
        needs_review = completeness < 0.5
        
        print(f"✅ Review decision: {'REQUIRED' if needs_review else 'AUTO-APPROVE'}")
        
        return {**state, "human_review_required": needs_review}
    
    def review_decision(self, state: RIAState) -> str:
        """Decision function for human review routing."""
        if state.get("human_review_required", False):
            return "review"
        return "approve"
    
    def human_review_checkpoint(self, state: RIAState) -> RIAState:
        """Human review checkpoint (interrupt for review)."""
        print(f"\n⏸️  Human review checkpoint...")
        print("   [In production, this would interrupt for human review]")
        
        # For now, auto-approve (in production, this would wait for human input)
        return {**state, "human_review_result": "approved"}
    
    def human_review_decision(self, state: RIAState) -> str:
        """Decision function after human review."""
        result = state.get("human_review_result", "approved")
        return result
    
    def generate_report_output(self, state: RIAState) -> RIAState:
        """Generate final report output."""
        print(f"\n📄 Generating report output...")
        
        structured = state.get("structured_assessment", {})
        
        # For now, just pass through structured assessment
        # In production, this would generate PDF, DOCX, HTML, etc.
        
        final_report = {
            **structured,
            "formats": ["json"],  # Could add "pdf", "docx", "html"
            "generated_at": datetime.now().isoformat()
        }
        
        print(f"✅ Report generated")
        
        return {**state, "final_report": final_report}
    
    def prepare_knowledge_base_update(self, state: RIAState) -> RIAState:
        """Prepare data for knowledge base update."""
        print(f"\n📚 Preparing knowledge base update...")
        
        proposal = state.get("proposal", "")
        structured = state.get("structured_assessment", {})
        features = state.get("features", {})
        
        kb_data = {
            "proposal_text": proposal,
            "categories": features.get("categories", []),
            "sections": structured.get("sections", {}),
            "metadata": structured.get("metadata", {})
        }
        
        print(f"✅ Knowledge base data prepared")
        
        return {**state, "kb_update_data": kb_data}
    
    def update_vector_store(self, state: RIAState) -> RIAState:
        """Update vector store with new proposal."""
        print(f"\n💾 Updating vector store...")
        
        # In production, this would:
        # 1. Chunk the proposal and assessment
        # 2. Generate embeddings
        # 3. Add to vector store
        # 4. Update BM25 index
        
        print(f"✅ Vector store updated (placeholder)")
        
        return state
    
    def update_knowledge_graph(self, state: RIAState) -> RIAState:
        """Update knowledge graph with new proposal."""
        print(f"\n🕸️  Updating knowledge graph...")
        
        # In production, this would:
        # 1. Create proposal node
        # 2. Link to categories
        # 3. Create chunk nodes
        # 4. Create relationships
        
        print(f"✅ Knowledge graph updated (placeholder)")
        
        return state
    
    def log_error(self, state: RIAState) -> RIAState:
        """Log error information."""
        errors = state.get("errors", [])
        print(f"\n❌ Errors logged: {len(errors)}")
        return state
    
    async def _openai_fallback(self, state: RIAState, query: str) -> RIAState:
        """Fallback to OpenAI when council is not available."""
        try:
            from openai import OpenAI
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return self._add_error(state, "No OpenAI API key found")
            
            client = OpenAI(api_key=api_key)
            
            # Build detailed prompt with Belgian RIA structure and EU analysis style
            themes_list = []
            for theme_num, theme_info in self.BELGIAN_IMPACT_THEMES.items():
                themes_list.append(f"[{theme_num}] {theme_info['name']}\n   Keywords: {theme_info['keywords']}")
            
            enhanced_query = f"""{query}

CRITICAL INSTRUCTIONS - BELGIAN RIA FORMAT WITH EU ANALYSIS STYLE:

You must generate a Belgian Regulatory Impact Assessment (RIA) that:
1. Uses the STANDARD BELGIAN RIA STRUCTURE with all 21 impact themes
2. Uses EU-STYLE DETAILED ANALYSIS (evidence-based, comprehensive, domain-specific)
3. Maps EU domain knowledge to Belgian categories where relevant

BELGIAN RIA STRUCTURE - 21 Impact Themes:
{chr(10).join(themes_list)}

For EACH of the 21 themes, you MUST provide:
1. Impact Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
2. Detailed Explanation: Use EU-style analysis with:
   - Evidence-based reasoning
   - Domain-specific insights (map EU domains to Belgian categories)
   - Quantitative/qualitative assessment where possible
   - Reference to relevant policy context
   - Consideration of direct and indirect impacts
3. Mitigation Measures (if negative impact): Specific measures to alleviate/compensate

EU ANALYSIS STYLE REQUIREMENTS:
- Use formal, evidence-based tone (like EU Impact Assessments)
- Provide detailed, comprehensive analysis (not just brief statements)
- Reference relevant domains (environment, health, economic, social, etc.)
- Consider baseline scenarios and policy options where relevant
- Use domain-specific terminology and concepts
- Provide structured, analytical reasoning
- Cite retrieved documents when using their analysis patterns or methodologies
- The Background/Problem Definition section should be comprehensive and define the problem clearly, drawing on similar problem definitions from retrieved EU documents where relevant

SPECIAL REQUIREMENTS FOR CERTAIN THEMES:
- Theme 3 (Equality between women and men): If applicable, address composition of affected groups, differences between women and men, problematic differences, and mitigation measures
- Theme 10 (SMEs): If applicable, detail affected sectors, number of enterprises, % of SMEs, and whether impacts are proportionally heavier on SMEs
- Theme 11 (Administrative burdens): If applicable, detail formalities, documents required, collection methods, periodicity, and measures to reduce burdens
- Theme 21 (Policy coherence for development): If applicable, assess impacts on developing countries across multiple domains

Structure your response as follows:
1. Background and Problem Definition (MOST IMPORTANT - define the problem, context, and why this regulation is needed)
2. Executive Summary
3. Proposal Overview
4. 21 Impact Themes Assessment (one section per theme, numbered [1] through [21])
5. Overall Assessment Summary
6. Recommendations

CITATION REQUIREMENTS:
- When referencing analysis patterns, methodologies, or evidence from the retrieved EU Impact Assessment documents, cite them using document references (e.g., "SWD(2022) 167 final", "COM(2022) 304 final")
- When referencing Belgian RIA examples, cite the document ID (e.g., "Belgian RIA 2014A03330.002")
- Include citations in parentheses after relevant statements, especially when:
  * Using similar problem definition approaches
  * Referencing comparable impact assessment methodologies
  * Citing evidence or data patterns from similar assessments
  * Drawing on policy option evaluation frameworks

Use EU analytical depth but maintain Belgian RIA form structure."""
            
            print("   Using OpenAI GPT-4 for Belgian RIA assessment (EU analysis style)...")
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert in both Belgian Regulatory Impact Assessments (RIA) and EU Impact Assessments. Your task is to generate Belgian RIA reports that:\n- Follow the standard Belgian RIA structure with all 21 impact themes\n- Use EU-style detailed, evidence-based analysis\n- Map EU domain knowledge to Belgian categories\n- Provide comprehensive assessments with clear positive/negative/no impact determinations for each theme\n- Use formal, analytical tone consistent with EU Impact Assessment documents\n- Include a Background/Problem Definition section as the FIRST and MOST IMPORTANT section\n- Cite retrieved documents (e.g., SWD references, COM references, Belgian RIA document IDs) when referencing their analysis patterns, methodologies, or evidence"},
                    {"role": "user", "content": enhanced_query}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Create mock stage results for compatibility
            stage1_results = [{"model": "gpt-4", "response": content}]
            stage2_results = [{"model": "gpt-4", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"]}]
            stage3_result = {"model": "gpt-4", "response": content}
            
            print("✅ OpenAI fallback complete")
            
            return {
                **state,
                "stage1_results": stage1_results,
                "stage2_results": stage2_results,
                "stage3_result": stage3_result
            }
        except Exception as e:
            return self._add_error(state, f"OpenAI fallback error: {str(e)}")
    
    def _add_error(self, state: RIAState, error_msg: str) -> RIAState:
        """Helper to add error to state."""
        errors = state.get("errors", [])
        errors.append({
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        return {**state, "errors": errors}


# ============================================================================
# Async Execution Wrapper
# ============================================================================

async def run_ria_workflow(
    proposal: str,
    context: Optional[Dict[str, Any]] = None,
    vector_store_path: str = "vector_store",
    knowledge_graph_path: str = "knowledge_graph.pkl"
) -> Dict[str, Any]:
    """
    Run the complete RIA workflow.
    
    Args:
        proposal: Regulatory proposal text
        context: Additional context (jurisdiction, category, year, etc.)
        vector_store_path: Path to vector store directory
        knowledge_graph_path: Path to knowledge graph pickle file
    
    Returns:
        Final state with generated assessment
    """
    workflow = RIAWorkflow(vector_store_path, knowledge_graph_path)
    
    # Initial state
    initial_state: RIAState = {
        "proposal": proposal,
        "context": context or {}
    }
    
    # Run workflow with reasonable recursion limit
    # Normal flow: ingest -> extract -> route -> retrieve -> merge -> check -> synthesize -> validate -> council -> extract -> structure -> quality -> review -> report -> kb -> END
    # That's about 15-20 steps, so 100 should be plenty even with a few retries
    config = {"recursion_limit": 100}
    final_state = await workflow.graph.ainvoke(initial_state, config=config)
    
    return final_state


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Example usage
    async def main():
        proposal = """Regulation on Artificial Intelligence: Establishing a framework for trustworthy AI systems, including requirements for high-risk AI applications, transparency obligations, and governance mechanisms for AI development and deployment in the European Union."""
        
        context = {
            "jurisdiction": "EU",
            "category": "Digital",
            "year": "2024",
            "document_type": "Impact Assessment"
        }
        
        result = await run_ria_workflow(proposal, context)
        
        print("\n" + "=" * 60)
        print("✅ Workflow Complete!")
        print("=" * 60)
        print(f"\nFinal Report:")
        if "final_report" in result:
            report = result["final_report"]
            print(f"  Sections: {len(report.get('sections', {}))}")
            print(f"  Sources: {len(report.get('sources', []))}")
            print(f"  Model: {report.get('metadata', {}).get('model', 'unknown')}")
    
    asyncio.run(main())
