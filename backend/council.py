"""3-stage LLM Council orchestration with bootstrap evaluation contexts and direct API support."""

import random
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from .config import (
    COUNCIL_MODELS, 
    CHAIRMAN_MODEL,
    ENABLE_BOOTSTRAP_EVALUATION,
    BOOTSTRAP_ITERATIONS,
    EVALUATION_CRITERIA,
    BOOTSTRAP_AGGREGATION_METHOD,
    USE_DIRECT_APIS
)

# Import API clients - use direct APIs only (no OpenRouter fallback)
if USE_DIRECT_APIS:
    try:
        from .direct_apis import query_models_parallel_direct as query_models_parallel, query_model_direct as query_model
        print("✅ Using direct APIs (Anthropic, Google, xAI, OpenAI)")
    except ImportError as e:
        raise RuntimeError(
            f"Direct APIs import failed: {e}. "
            "Please ensure all API keys are set in .env file. "
            "OpenRouter is not used in this system."
        )
else:
    raise RuntimeError(
        "No direct API keys found. Please set API keys in .env file:\n"
        "  - OPENAI_API_KEY\n"
        "  - ANTHROPIC_API_KEY\n"
        "  - GOOGLE_API_KEY\n"
        "  - XAI_API_KEY\n"
        "OpenRouter is not used in this system."
    )


async def stage1_collect_responses(
    user_query: str,
    context: Optional[str] = None,
    specialized_roles: bool = True
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.
    
    For RIA generation, models are assigned specialized roles:
    - Claude: Policy analysis specialist
    - Gemini: Evidence synthesis and data interpretation specialist
    - Grok: Impact assessment and risk analysis specialist

    Args:
        user_query: The user's question
        context: Optional retrieved context from vector store/knowledge graph
        specialized_roles: Whether to use specialized role prompts for RIA

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    # Build context-aware query
    if context and specialized_roles:
        # Create specialized prompts for each model based on their strengths
        specialized_queries = {}
        
        # Assign specialized roles based on model type
        for i, model in enumerate(COUNCIL_MODELS):
            if "google" in model or "gemini" in model:
                # Gemini: Evidence synthesis specialist
                specialized_queries[model] = f"""{user_query}

You are an Evidence Synthesis and Data Interpretation Specialist. Focus on:
- Synthesizing evidence from retrieved documents
- Proper citation of EU and Belgian RIA examples
- Data-driven impact assessments

Retrieved Context:
{context[:2000] if len(context) > 2000 else context}

Generate assessments with strong evidence-based reasoning and proper citations."""
            elif "x-ai" in model or "grok" in model:
                # Grok: Impact assessment specialist
                specialized_queries[model] = f"""{user_query}

You are an Impact Assessment and Risk Analysis Specialist. Focus on:
- Comprehensive 21 impact themes assessment
- Risk identification and mitigation measures
- Positive/negative/no impact determinations

Retrieved Context:
{context[:2000] if len(context) > 2000 else context}

Generate detailed impact assessments for all 21 Belgian RIA themes."""
            elif "openai" in model or "gpt" in model:
                # OpenAI: General analysis specialist
                specialized_queries[model] = f"""{user_query}

You are a Policy Analysis and General Analysis Specialist. Focus on:
- Policy context and regulatory analysis
- Drawing insights from retrieved EU Impact Assessment documents
- Comprehensive impact assessment structure

Retrieved Context:
{context[:2000] if len(context) > 2000 else context}

Generate a comprehensive assessment structure with detailed analysis."""
        
        # Use specialized queries if available, otherwise use general query
        queries = {}
        for model in COUNCIL_MODELS:
            if model in specialized_queries:
                queries[model] = specialized_queries[model]
            else:
                queries[model] = f"""{user_query}

Retrieved Context:
{context[:2000] if len(context) > 2000 else context}"""
    else:
        # Standard query for all models
        full_query = user_query
        if context:
            full_query = f"""{user_query}

Retrieved Context:
{context[:2000] if len(context) > 2000 else context}"""
        queries = {model: full_query for model in COUNCIL_MODELS}
    
    # Query all models in parallel with their specialized queries
    tasks = []
    model_list = []
    for model, query in queries.items():
        messages = [{"role": "user", "content": query}]
        tasks.append(query_model(model, messages))
        model_list.append(model)
    
    import asyncio
    responses_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Format results
    stage1_results = []
    for model, response in zip(model_list, responses_list):
        if isinstance(response, Exception):
            print(f"Error from {model}: {response}")
            continue
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


def _generate_evaluation_prompt(
    user_query: str,
    responses_text: str,
    criterion: Dict[str, str],
    context: Optional[str] = None
) -> str:
    """
    Generate an evaluation prompt based on a specific criterion.
    For RIA assessments, includes context-aware evaluation.
    
    Args:
        user_query: The original user query
        responses_text: Formatted responses text
        criterion: Dictionary with 'name', 'focus', and 'description'
        context: Optional retrieved context for evaluation
    
    Returns:
        Formatted evaluation prompt
    """
    context_section = ""
    if context:
        context_section = f"""

Retrieved Context (for reference):
{context[:1500] if len(context) > 1500 else context}

Evaluate how well each response uses this retrieved context."""
    
    return f"""You are evaluating Belgian RIA impact assessments for {criterion['focus']}.

Original Query: {user_query}
{context_section}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. Evaluate each response based on {criterion['description']}.
2. For each response, explain what it does well and what it does poorly, focusing on {criterion['focus']}.
3. Pay special attention to:
   - Adherence to Belgian RIA structure (21 impact themes)
   - Quality of EU-style detailed analysis
   - Proper use of retrieved context and citations
   - Completeness of 21 Impact Themes Assessment (all themes must be assessed)
4. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking focusing on {criterion['focus']}:"""


def _shuffle_responses_order(
    labels: List[str],
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Shuffle the order of responses while maintaining label-response pairing.
    
    Args:
        labels: List of response labels
        stage1_results: List of response dictionaries
    
    Returns:
        Tuple of (shuffled_labels, shuffled_results)
    """
    # Create pairs and shuffle
    pairs = list(zip(labels, stage1_results))
    random.shuffle(pairs)
    shuffled_labels, shuffled_results = zip(*pairs)
    return list(shuffled_labels), list(shuffled_results)


def _aggregate_bootstrap_rankings_borda(
    bootstrap_results: List[Dict[str, Any]],
    num_responses: int
) -> Dict[str, float]:
    """
    Aggregate bootstrap rankings using Borda Count method.
    
    Args:
        bootstrap_results: List of ranking results from bootstrap iterations
        num_responses: Total number of responses being ranked
    
    Returns:
        Dictionary mapping response labels to Borda scores
    """
    label_scores = defaultdict(float)
    
    for result in bootstrap_results:
        parsed_ranking = result.get('parsed_ranking', [])
        for position, label in enumerate(parsed_ranking, start=1):
            # Borda count: 1st place gets N points, 2nd gets N-1, etc.
            points = num_responses - position + 1
            label_scores[label] += points
    
    return dict(label_scores)


def _aggregate_bootstrap_rankings_position_average(
    bootstrap_results: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Aggregate bootstrap rankings using position averaging.
    
    Args:
        bootstrap_results: List of ranking results from bootstrap iterations
    
    Returns:
        Dictionary mapping response labels to average positions
    """
    label_positions = defaultdict(list)
    
    for result in bootstrap_results:
        parsed_ranking = result.get('parsed_ranking', [])
        for position, label in enumerate(parsed_ranking, start=1):
            label_positions[label].append(position)
    
    # Calculate average position for each label
    label_averages = {}
    for label, positions in label_positions.items():
        label_averages[label] = sum(positions) / len(positions)
    
    return label_averages


def _aggregate_bootstrap_rankings_consensus_score(
    bootstrap_results: List[Dict[str, Any]],
    num_responses: int
) -> Dict[str, float]:
    """
    Aggregate bootstrap rankings using consensus scoring.
    Rewards consistent high rankings.
    
    Args:
        bootstrap_results: List of ranking results from bootstrap iterations
        num_responses: Total number of responses being ranked
    
    Returns:
        Dictionary mapping response labels to consensus scores
    """
    label_scores = defaultdict(float)
    
    for result in bootstrap_results:
        parsed_ranking = result.get('parsed_ranking', [])
        for position, label in enumerate(parsed_ranking, start=1):
            # Consensus score: higher positions get exponentially more weight
            # 1st = 3 points, 2nd = 2 points, 3rd = 1 point (for 3 responses)
            points = num_responses - position + 1
            label_scores[label] += points
    
    return dict(label_scores)


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    context: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses using bootstrap evaluation contexts.
    
    This implements bootstrap evaluation contexts to reduce pattern recognition bias:
    - Varies evaluation criteria (accuracy, completeness, clarity, utility, balanced)
    - Varies response presentation order
    - Aggregates rankings using consensus methods
    
    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
    
    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Handle empty results
    if not stage1_results or len(stage1_results) == 0:
        print("⚠️  No Stage 1 results to rank - returning empty rankings")
        return [], {}
    
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...
    
    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }
    
    if not ENABLE_BOOTSTRAP_EVALUATION:
        # Fallback to original single evaluation method
        responses_text = "\n\n".join([
            f"Response {label}:\n{result['response']}"
            for label, result in zip(labels, stage1_results)
        ])
        
        ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

        messages = [{"role": "user", "content": ranking_prompt}]
        responses = await query_models_parallel(COUNCIL_MODELS, messages)
        
        stage2_results = []
        for model, response in responses.items():
            if response is not None:
                full_text = response.get('content', '')
                parsed = parse_ranking_from_text(full_text)
                stage2_results.append({
                    "model": model,
                    "ranking": full_text,
                    "parsed_ranking": parsed
                })
        
        return stage2_results, label_to_model
    
    # Bootstrap evaluation contexts implementation
    all_bootstrap_results = []
    
    # Determine number of iterations and criteria to use
    num_iterations = min(BOOTSTRAP_ITERATIONS, len(EVALUATION_CRITERIA))
    criteria_to_use = EVALUATION_CRITERIA[:num_iterations]
    
    # If we need more iterations than criteria, cycle through criteria
    if BOOTSTRAP_ITERATIONS > len(EVALUATION_CRITERIA):
        criteria_to_use = (EVALUATION_CRITERIA * ((BOOTSTRAP_ITERATIONS // len(EVALUATION_CRITERIA)) + 1))[:BOOTSTRAP_ITERATIONS]
    
    # Run bootstrap iterations
    for iteration in range(BOOTSTRAP_ITERATIONS):
        criterion = criteria_to_use[iteration]
        
        # Vary response order for each iteration
        shuffled_labels, shuffled_results = _shuffle_responses_order(labels.copy(), stage1_results.copy())
        
        # Build responses text with shuffled order
        responses_text = "\n\n".join([
            f"Response {label}:\n{result['response']}"
            for label, result in zip(shuffled_labels, shuffled_results)
        ])
        
        # Generate evaluation prompt with specific criterion and context
        ranking_prompt = _generate_evaluation_prompt(user_query, responses_text, criterion, context)
        
        messages = [{"role": "user", "content": ranking_prompt}]
        
        # Get rankings from all council models in parallel for this iteration
        responses = await query_models_parallel(COUNCIL_MODELS, messages)
        
        # Store results with iteration metadata
        for model, response in responses.items():
            if response is not None:
                full_text = response.get('content', '')
                parsed = parse_ranking_from_text(full_text)
                
                # Map shuffled labels back to original labels for consistency
                # Create reverse mapping from shuffled to original
                shuffled_to_original = {
                    shuffled_labels[i]: labels[i]
                    for i in range(len(labels))
                }
                
                # Convert parsed ranking back to original labels
                original_parsed = [
                    shuffled_to_original.get(label, label)
                    for label in parsed
                    if label in shuffled_to_original
                ]
                
                all_bootstrap_results.append({
                    "model": model,
                    "ranking": full_text,
                    "parsed_ranking": original_parsed,
                    "iteration": iteration,
                    "criterion": criterion['name'],
                    "order": shuffled_labels.copy()
                })
    
    # Aggregate bootstrap rankings for each model
    stage2_results = []
    models_seen = set()
    
    for model in COUNCIL_MODELS:
        if model in models_seen:
            continue
        models_seen.add(model)
        
        # Get all bootstrap results for this model
        model_bootstrap_results = [
            r for r in all_bootstrap_results
            if r['model'] == model
        ]
        
        if not model_bootstrap_results:
            continue
        
        # Aggregate rankings based on configured method
        if BOOTSTRAP_AGGREGATION_METHOD == "borda_count":
            aggregated_scores = _aggregate_bootstrap_rankings_borda(
                model_bootstrap_results,
                len(stage1_results)
            )
        elif BOOTSTRAP_AGGREGATION_METHOD == "position_average":
            aggregated_scores = _aggregate_bootstrap_rankings_position_average(
                model_bootstrap_results
            )
        elif BOOTSTRAP_AGGREGATION_METHOD == "consensus_score":
            aggregated_scores = _aggregate_bootstrap_rankings_consensus_score(
                model_bootstrap_results,
                len(stage1_results)
            )
        else:
            # Default to Borda count
            aggregated_scores = _aggregate_bootstrap_rankings_borda(
                model_bootstrap_results,
                len(stage1_results)
            )
        
        # Sort labels by aggregated score (higher is better for Borda/Consensus, lower for average)
        if BOOTSTRAP_AGGREGATION_METHOD == "position_average":
            sorted_labels = sorted(aggregated_scores.items(), key=lambda x: x[1])
        else:
            sorted_labels = sorted(aggregated_scores.items(), key=lambda x: x[1], reverse=True)
        
        final_ranking = [label for label, score in sorted_labels]
        
        # Create aggregated ranking text
        ranking_text_parts = [
            f"Bootstrap Evaluation Summary (Method: {BOOTSTRAP_AGGREGATION_METHOD})",
            f"Iterations: {len(model_bootstrap_results)}",
            f"Criteria used: {', '.join(set(r['criterion'] for r in model_bootstrap_results))}",
            "",
            "FINAL RANKING:"
        ]
        ranking_text_parts.extend([
            f"{i+1}. {label}" for i, label in enumerate(final_ranking)
        ])
        
        stage2_results.append({
            "model": model,
            "ranking": "\n".join(ranking_text_parts),
            "parsed_ranking": final_ranking,
            "bootstrap_iterations": len(model_bootstrap_results),
            "aggregation_method": BOOTSTRAP_AGGREGATION_METHOD
        })
    
    return stage2_results, label_to_model


# Theme definitions for chunked generation
THEME_DEFINITIONS = {
    1: {
        "name": "Fight against poverty",
        "keywords": "Revenu minimum conforme à la dignité humaine, accès à des services de qualité, surendettement, risque de pauvreté ou d'exclusion sociale (y compris chez les mineurs), illettrisme, fracture numérique"
    },
    2: {
        "name": "Equal opportunities and social cohesion",
        "keywords": "Non-discrimination, égalité de traitement, accès aux biens et services, accès à l'information, à l'éducation et à la formation, écart de revenu, effectivité des droits civils, politiques et sociaux (en particulier pour les populations fragilisées, les enfants, les personnes âgées, les personnes handicapées et les minorités)"
    },
    3: {
        "name": "Equality between women and men",
        "keywords": "Accès des femmes et des hommes aux ressources: revenus, travail, responsabilités, santé/soins/bien-être, sécurité, éducation/savoir/formation, mobilité, temps, loisirs, etc. Exercice des droits fondamentaux par les femmes et les hommes droits civils, sociaux et politiques"
    },
    4: {
        "name": "Health",
        "keywords": "Accès aux soins de santé de qualité, efficacité de l'offre de soins, espérance de vie en bonne santé, traitements des maladies chroniques (maladies cardiovasculaires, cancers, diabètes et maladies respiratoires chroniques), déterminants de la santé (niveau socio-économique, alimentation, pollution), qualité de la vie"
    },
    5: {
        "name": "Employment",
        "keywords": "Accès au marché de l'emploi, emplois de qualité, chômage, travail au noir, conditions de travail et de licenciement, carrière, temps de travail, bien-être au travail, accidents de travail, maladies professionnelles, équilibre vie privée - vie professionnelle, rémunération convenable, possibilités de formation professionnelle, relations collectives de travail"
    },
    6: {
        "name": "Consumption and production patterns",
        "keywords": "Stabilité/prévisibilité des prix, information et protection du consommateur, utilisation efficace des ressources, évaluation et intégration des externalités (environnementales et sociales) tout au long du cycle de vie des produits et services, modes de gestion des organisations"
    },
    7: {
        "name": "Economic development",
        "keywords": "Création d'entreprises, production de biens et de services, productivité du travail et des ressources/matières premières, facteurs de compétitivité, accès au marché et à la profession, transparence du marché, accès aux marchés publics, relations commerciales et financières internationales, balance des importations/exportations, économie souterraine, sécurité d'approvisionnement des ressources énergétiques, minérales et organiques"
    },
    8: {
        "name": "Investments",
        "keywords": "Investissements en capital physique (machines, véhicules, infrastructures), technologique, intellectuel (logiciel, recherche et développement) et humain, niveau d'investissement net en pourcentage du PIB"
    },
    9: {
        "name": "Research and development",
        "keywords": "Opportunités de recherche et développement, innovation par l'introduction et la diffusion de nouveaux modes de production, de nouvelles pratiques d'entreprises ou de nouveaux produits et services, dépenses de recherche et de développement"
    },
    10: {
        "name": "SMEs (Small and Medium-Sized Enterprises)",
        "keywords": "Impact sur le développement des PME"
    },
    11: {
        "name": "Administrative burdens",
        "keywords": "Réduction des formalités et des obligations administratives liées directement ou indirectement à l'exécution, au respect et/ou au maintien d'un droit, d'une interdiction ou d'une obligation"
    },
    12: {
        "name": "Energy",
        "keywords": "Mix énergétique (bas carbone, renouvelable, fossile), utilisation de la biomasse (bois, biocarburants), efficacité énergétique, consommation d'énergie de l'industrie, des services, des transports et des ménages, sécurité d'approvisionnement, accès aux biens et services énergétiques"
    },
    13: {
        "name": "Mobility",
        "keywords": "Volume de transport (nombre de kilomètres parcourus et nombre de véhicules), offre de transports collectifs, offre routière, ferroviaire, maritime et fluviale pour les transports de marchandises, répartitions des modes de transport (modal shift), sécurité, densité du trafic"
    },
    14: {
        "name": "Food",
        "keywords": "Accès à une alimentation sûre (contrôle de qualité), alimentation saine et à haute valeur nutritionnelle, gaspillages, commerce équitable"
    },
    15: {
        "name": "Climate change",
        "keywords": "Émissions de gaz à effet de serre, capacité d'adaptation aux effets des changements climatiques, résilience, transition énergétique, sources d'énergies renouvelables, utilisation rationnelle de l'énergie, efficacité énergétique, performance énergétique des bâtiments, piégeage du carbone"
    },
    16: {
        "name": "Natural resources",
        "keywords": "Gestion efficiente des ressources, recyclage, réutilisation, qualité et consommation de l'eau (eaux de surface et souterraines, mers et océans), qualité et utilisation du sol (pollution, teneur en matières organiques, érosion, assèchement, inondations, densification, fragmentation), déforestation"
    },
    17: {
        "name": "Indoor and outdoor air",
        "keywords": "Qualité de l'air (y compris l'air intérieur), émissions de polluants (agents chimiques ou biologiques méthane, hydrocarbures, solvants, SOX, NOx, NH3), particules fines"
    },
    18: {
        "name": "Biodiversity",
        "keywords": "Niveaux de la diversité biologique, état des écosystèmes (restauration, conservation, valorisation, zones protégées), altération et fragmentation des habitats, biotechnologies, brevets d'invention sur la matière biologique, utilisation des ressources génétiques, services rendus par les écosystèmes (purification de l'eau et de l'air, ...), espèces domestiquées ou cultivées, espèces exotiques envahissantes, espèces menacées"
    },
    19: {
        "name": "Nuisances",
        "keywords": "Nuisances sonores, visuelles ou olfactives, vibrations, rayonnements ionisants, non ionisants et électromagnétiques, nuisances lumineuses"
    },
    20: {
        "name": "Public authorities",
        "keywords": "Fonctionnement démocratique des organes de concertation et consultation, services publics aux usagers, plaintes, recours, contestations, mesures d'exécution, investissements publics"
    },
    21: {
        "name": "Policy coherence for development",
        "keywords": "Prise en considération des impacts involontaires des mesures politiques belges sur les intérêts des pays en voie de développement"
    }
}


async def _generate_theme_batch(
    user_query: str,
    stage1_text: str,
    stage2_text: str,
    context_section: str,
    theme_numbers: List[int],
    batch_num: int,
    total_batches: int
) -> str:
    """
    Generate assessment for a batch of themes (chunked generation optimization).
    
    Args:
        user_query: Original proposal query
        stage1_text: Stage 1 responses text
        stage2_text: Stage 2 rankings text
        context_section: Retrieved context
        theme_numbers: List of theme numbers to generate (e.g., [1, 2, 3, 4, 5, 6, 7])
        batch_num: Current batch number (1, 2, or 3)
        total_batches: Total number of batches (3)
    
    Returns:
        Generated text for the theme batch
    """
    # Build theme format section for this batch only
    themes_format = ""
    for theme_num in theme_numbers:
        theme_def = THEME_DEFINITIONS[theme_num]
        themes_format += f"""
[{theme_num}] {theme_def['name']}
Keywords: {theme_def['keywords']}
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words explaining the impact determination]
🚨 IF EUROSTAT DATA IS PROVIDED FOR THIS THEME: You MUST include a citation with actual quantitative values (e.g., "According to Eurostat (ilc_li02, Belgium, 2022), the rate was 15.3%") to QUANTIFY your statements. DO NOT write generic statements.

"""
    
    batch_prompt = f"""You are the Meta-Chairman of an LLM Council for Belgian Regulatory Impact Assessment generation. Multiple AI models have provided specialized responses, and then ranked each other's responses.

Original Query: {user_query}
{context_section}

STAGE 1 - Individual Responses (from specialized models):
{stage1_text[:3000]}...

STAGE 2 - Peer Rankings:
{stage2_text[:1500]}...

Your task: Generate assessments for themes [{theme_numbers[0]}] through [{theme_numbers[-1]}] ONLY.

CRITICAL REQUIREMENTS:
1. You MUST assess ONLY themes {theme_numbers} in this batch (batch {batch_num} of {total_batches})
2. Each theme MUST have:
   - Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
   - Detailed explanation (minimum 150 words)
   - Eurostat citation with quantitative values if data is provided
3. Use retrieved context and Eurostat data provided above
4. DO NOT include any other sections (Executive Summary, Proposal Overview, etc.)

MANDATORY FORMAT FOR THIS BATCH:
{themes_format}

Generate ONLY the assessments for themes {theme_numbers}. Start directly with theme [{theme_numbers[0]}] and end with theme [{theme_numbers[-1]}]."""

    messages = [{"role": "user", "content": batch_prompt}]
    response = await query_model(CHAIRMAN_MODEL, messages, timeout=120.0)  # Reduced timeout per batch
    
    if response is None:
        return f"\n[Error generating batch {batch_num}]\n"
    
    return response.get('content', '')


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    context: Optional[str] = None,
    retry_attempt: int = 0,
    use_chunked_generation: bool = True
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.
    For RIA assessments, ensures comprehensive synthesis with context awareness.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        context: Optional retrieved context from vector store/knowledge graph

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    context_section = ""
    if context:
        # OPTIMIZATION: Reduced context limit - Eurostat is now compressed (one stat per theme)
        # Use 5000 chars (reduced from 8000) since Eurostat data is now more compact
        context_limit = 5000
        truncated_context = context[:context_limit] if len(context) > context_limit else context
        
        # If we truncated, try to preserve Eurostat section if it exists
        if len(context) > context_limit and "Eurostat Statistical Data" in context:
            # Find where Eurostat section ends
            eurostat_end = context.find("=" * 70, context.find("CRITICAL: MANDATORY EUROSTAT DATA USAGE"))
            if eurostat_end != -1:
                # Include full Eurostat section + some document context
                eurostat_section = context[:eurostat_end + 100]
                remaining_chars = context_limit - len(eurostat_section)
                if remaining_chars > 0:
                    # Add document context after Eurostat
                    doc_section_start = context.find("RELEVANT DOCUMENTS", eurostat_end)
                    if doc_section_start != -1:
                        doc_section = context[doc_section_start:doc_section_start + remaining_chars]
                        truncated_context = eurostat_section + "\n\n" + doc_section
                    else:
                        truncated_context = eurostat_section + context[eurostat_end + 100:eurostat_end + 100 + remaining_chars]
        
        context_section = f"""

RETRIEVED CONTEXT (from EU and Belgian RIA documents):
{truncated_context}

Use this context to ensure your synthesis:
- References specific documents where appropriate (e.g., SWD(2022) 167 final)
- Uses similar analysis patterns from retrieved EU documents
- Maintains consistency with Belgian RIA structure
- 🚨 CRITICAL: If Eurostat statistical data is provided above, you MUST use it with citations and quantitative values"""

    # Add retry warning if this is a retry
    retry_warning = ""
    if retry_attempt > 0:
        retry_warning = f"""

⚠️⚠️⚠️ CRITICAL: THIS IS A RETRY ATTEMPT ⚠️⚠️⚠️
The previous response did not include all 21 required impact themes. 
You MUST include ALL 21 themes numbered [1] through [21] in your response.
DO NOT skip any themes. Assess each one as POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT.
Your response will be rejected again if it does not contain all 21 themes.

"""
    
    chairman_prompt = f"""You are the Meta-Chairman of an LLM Council for Belgian Regulatory Impact Assessment generation. Multiple AI models have provided specialized responses, and then ranked each other's responses.
{retry_warning}
Original Query: {user_query}
{context_section}

STAGE 1 - Individual Responses (from specialized models):
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Meta-Chairman is to synthesize all of this information into a single, comprehensive Belgian RIA assessment. 

CRITICAL REQUIREMENTS:
1. Structure: 21 Impact Themes Assessment ONLY
   - DO NOT include Executive Summary
   - DO NOT include Proposal Overview
   - DO NOT include Overall Assessment Summary
   - Your report MUST contain ONLY the "21 Belgian Impact Themes Assessment" section
2. FORBIDDEN SECTIONS - CRITICAL: DO NOT include ANY of the following sections ANYWHERE in your report:
   - Current Legal Framework (or "Legal Framework")
   - Problem Identification
   - Policy Objectives
   - Stakeholders Affected (or "Stakeholders")
   These sections are FORBIDDEN and must NOT appear as standalone sections, subsections, or within any other section.
   If you mention legal context, problems, objectives, or stakeholders, integrate them naturally into the theme assessments WITHOUT creating separate sections with these titles.
3. Use retrieved context: Reference specific EU documents (SWD, COM references) and Belgian RIA examples where relevant
3. Use Eurostat data: If Eurostat statistical data is provided in the context, you MUST:
   - 🚨 MANDATORY: For EVERY theme where Eurostat data is provided, you MUST include the citation WITH actual quantitative values
   - The data is formatted as "READY-TO-USE CITATION" - copy it directly into your assessment text
   - The PURPOSE is to QUANTIFY your statements - you MUST include the numbers/percentages provided
   - Example CORRECT: "According to Eurostat (ilc_li02, Belgium, 2022), the at-risk-of-poverty rate for persons aged 65+ in Belgium was 15.3%"
   - Example CORRECT: "Eurostat data (ilc_li02, Belgium, 2022) shows that the at-risk-of-poverty rate was 15.3%, with breakdowns showing rates of 4.0% for children under 6 years, 2.9% for males overall, and 3.4% for males under 6 years"
   - Example WRONG: "According to Eurostat data, poverty is an issue" [missing citation and values - REJECTED]
   - Example WRONG: "According to Eurostat (ilc_li02, Belgium, 2022)" [missing actual statistic - REJECTED]
   - Use the actual values to establish baseline conditions and QUANTIFY expected impacts
   - Format statistics clearly with units (%, thousands, billions, etc.) and context (age groups, gender, etc.)
   - Count how many themes have Eurostat data - you must cite at least 80% of them
   - Your response will be REJECTED if you ignore available Eurostat data and write generic statements instead
4. Citations: Include citations when referencing analysis patterns or methodologies from retrieved documents AND when using Eurostat statistics. For themes with Eurostat data provided, you MUST cite it.
5. Completeness: Ensure all 21 impact themes are assessed with clear positive/negative/no impact determinations
6. Quality: Use EU-style detailed, evidence-based analysis while maintaining Belgian RIA form structure. When Eurostat data is available, integrate it naturally into your analysis to provide quantitative context with actual numbers
7. FORBIDDEN CONTENT - ABSOLUTE PROHIBITION: 
   DO NOT create sections titled:
   - "Current Legal Framework" or "Legal Framework"
   - "Problem Identification" 
   - "Policy Objectives"
   - "Stakeholders Affected" or "Stakeholders"
   
   These section titles are FORBIDDEN. If you need to discuss legal context, problems, objectives, or stakeholders, integrate them into the theme assessments WITHOUT using these specific section titles. Your response will be REJECTED if these section titles appear.
   
   FORBIDDEN SECTIONS - ALSO DO NOT INCLUDE:
   - Executive Summary
   - Proposal Overview
   - Overall Assessment Summary
   - Recommendations
   - Conclusion
   
   Your report MUST contain ONLY the "21 Belgian Impact Themes Assessment" section.

MANDATORY FORMAT FOR 21 BELGIAN IMPACT THEMES ASSESSMENT:
You MUST assess ALL 21 Belgian RIA themes using EXACTLY this format:

[1] Fight against poverty
Keywords: Revenu minimum conforme à la dignité humaine, accès à des services de qualité, surendettement, risque de pauvreté ou d'exclusion sociale (y compris chez les mineurs), illettrisme, fracture numérique
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words explaining the impact determination]
🚨 IF EUROSTAT DATA IS PROVIDED FOR THIS THEME: You MUST include a citation with actual quantitative values (e.g., "According to Eurostat (ilc_li02, Belgium, 2022), the rate was 15.3%") to QUANTIFY your statements. DO NOT write generic statements.
IMPORTANT: If Eurostat data is provided for this theme in the context, you MUST include a citation with actual quantitative values (e.g., "According to Eurostat (ilc_li02, Belgium, 2022), the rate was 15.3%") to QUANTIFY your statements.

[2] Equal opportunities and social cohesion
Keywords: Non-discrimination, égalité de traitement, accès aux biens et services, accès à l'information, à l'éducation et à la formation, écart de revenu, effectivité des droits civils, politiques et sociaux (en particulier pour les populations fragilisées, les enfants, les personnes âgées, les personnes handicapées et les minorités)
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[3] Equality between women and men
Keywords: Accès des femmes et des hommes aux ressources: revenus, travail, responsabilités, santé/soins/bien-être, sécurité, éducation/savoir/formation, mobilité, temps, loisirs, etc. Exercice des droits fondamentaux par les femmes et les hommes droits civils, sociaux et politiques
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[4] Health
Keywords: Accès aux soins de santé de qualité, efficacité de l'offre de soins, espérance de vie en bonne santé, traitements des maladies chroniques (maladies cardiovasculaires, cancers, diabètes et maladies respiratoires chroniques), déterminants de la santé (niveau socio-économique, alimentation, pollution), qualité de la vie
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[5] Employment
Keywords: Accès au marché de l'emploi, emplois de qualité, chômage, travail au noir, conditions de travail et de licenciement, carrière, temps de travail, bien-être au travail, accidents de travail, maladies professionnelles, équilibre vie privée - vie professionnelle, rémunération convenable, possibilités de formation professionnelle, relations collectives de travail
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[6] Consumption and production patterns
Keywords: Stabilité/prévisibilité des prix, information et protection du consommateur, utilisation efficace des ressources, évaluation et intégration des externalités (environnementales et sociales) tout au long du cycle de vie des produits et services, modes de gestion des organisations
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[7] Economic development
Keywords: Création d'entreprises, production de biens et de services, productivité du travail et des ressources/matières premières, facteurs de compétitivité, accès au marché et à la profession, transparence du marché, accès aux marchés publics, relations commerciales et financières internationales, balance des importations/exportations, économie souterraine, sécurité d'approvisionnement des ressources énergétiques, minérales et organiques
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[8] Investments
Keywords: Investissements en capital physique (machines, véhicules, infrastructures), technologique, intellectuel (logiciel, recherche et développement) et humain, niveau d'investissement net en pourcentage du PIB
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[9] Research and development
Keywords: Opportunités de recherche et développement, innovation par l'introduction et la diffusion de nouveaux modes de production, de nouvelles pratiques d'entreprises ou de nouveaux produits et services, dépenses de recherche et de développement
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[10] SMEs (Small and Medium-Sized Enterprises)
Keywords: Impact sur le développement des PME
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[11] Administrative burdens
Keywords: Réduction des formalités et des obligations administratives liées directement ou indirectement à l'exécution, au respect et/ou au maintien d'un droit, d'une interdiction ou d'une obligation
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[12] Energy
Keywords: Mix énergétique (bas carbone, renouvelable, fossile), utilisation de la biomasse (bois, biocarburants), efficacité énergétique, consommation d'énergie de l'industrie, des services, des transports et des ménages, sécurité d'approvisionnement, accès aux biens et services énergétiques
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[13] Mobility
Keywords: Volume de transport (nombre de kilomètres parcourus et nombre de véhicules), offre de transports collectifs, offre routière, ferroviaire, maritime et fluviale pour les transports de marchandises, répartitions des modes de transport (modal shift), sécurité, densité du trafic
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[14] Food
Keywords: Accès à une alimentation sûre (contrôle de qualité), alimentation saine et à haute valeur nutritionnelle, gaspillages, commerce équitable
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[15] Climate change
Keywords: Émissions de gaz à effet de serre, capacité d'adaptation aux effets des changements climatiques, résilience, transition énergétique, sources d'énergies renouvelables, utilisation rationnelle de l'énergie, efficacité énergétique, performance énergétique des bâtiments, piégeage du carbone
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[16] Natural resources
Keywords: Gestion efficiente des ressources, recyclage, réutilisation, qualité et consommation de l'eau (eaux de surface et souterraines, mers et océans), qualité et utilisation du sol (pollution, teneur en matières organiques, érosion, assèchement, inondations, densification, fragmentation), déforestation
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[17] Indoor and outdoor air
Keywords: Qualité de l'air (y compris l'air intérieur), émissions de polluants (agents chimiques ou biologiques méthane, hydrocarbures, solvants, SOX, NOx, NH3), particules fines
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[18] Biodiversity
Keywords: Niveaux de la diversité biologique, état des écosystèmes (restauration, conservation, valorisation, zones protégées), altération et fragmentation des habitats, biotechnologies, brevets d'invention sur la matière biologique, utilisation des ressources génétiques, services rendus par les écosystèmes (purification de l'eau et de l'air, ...), espèces domestiquées ou cultivées, espèces exotiques envahissantes, espèces menacées
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[19] Nuisances
Keywords: Nuisances sonores, visuelles ou olfactives, vibrations, rayonnements ionisants, non ionisants et électromagnétiques, nuisances lumineuses
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[20] Public authorities
Keywords: Fonctionnement démocratique des organes de concertation et consultation, services publics aux usagers, plaintes, recours, contestations, mesures d'exécution, investissements publics
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

[21] Policy coherence for development
Keywords: Prise en considération des impacts involontaires des mesures politiques belges sur les intérêts des pays en voie de développement
Assessment: [POSITIVE IMPACT] / [NEGATIVE IMPACT] / [NO IMPACT]
[Detailed explanation with EU-style analysis - minimum 150 words]

CRITICAL REQUIREMENTS FOR 21 THEMES - THIS IS MANDATORY:
1. You MUST assess ALL 21 themes numbered [1] through [21] - NO EXCEPTIONS, NO SKIPPING
2. You MUST provide an actual assessment (POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT) for EACH theme
3. FORBIDDEN: DO NOT use "MIXED IMPACT" - this is NOT a valid assessment type. You MUST choose ONE of: POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT
4. If a theme has both positive and negative aspects, you MUST determine which is the NET/OVERALL impact and choose POSITIVE IMPACT or NEGATIVE IMPACT accordingly
5. DO NOT skip any themes - even if the impact is minimal or zero, you MUST still assess it as NO IMPACT with a detailed explanation
6. DO NOT write "Not assessed" - you must analyze each theme and determine its impact based on the proposal
7. Each assessment must include a detailed explanation of at least 150 words explaining why you determined that impact
8. 🚨 MANDATORY EUROSTAT CITATIONS: For EVERY theme where Eurostat data is provided in the context, you MUST include at least ONE citation with actual quantitative values (percentages, numbers) to QUANTIFY your statements. Look for "READY-TO-USE CITATION" format above and copy it into your text. DO NOT write generic statements when specific data is available.
9. The themes section MUST contain exactly 21 theme assessments, numbered [1] through [21] in sequence
10. If a theme has NO IMPACT, you must still provide a detailed explanation (minimum 150 words) explaining why there is no impact
11. DO NOT only assess themes with positive impacts - you MUST assess ALL themes, including those with negative or no impact
12. Your response will be REJECTED if it does not contain all 21 theme assessments
13. Your response will be REJECTED if you use "MIXED IMPACT" - only POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT are allowed
14. Your response will be REJECTED if you ignore available Eurostat data and write generic unquantified statements

MANDATORY STRUCTURE FOR THEMES SECTION:
Your "21 Belgian Impact Themes Assessment" section MUST follow this EXACT structure:

## 21 Belgian Impact Themes Assessment

[1] Fight against poverty
Keywords: [keywords]
Assessment: [POSITIVE IMPACT / NEGATIVE IMPACT / NO IMPACT]
[150+ word explanation - MUST include Eurostat citation with quantitative values if data is provided]

[2] Equal opportunities and social cohesion
Keywords: [keywords]
Assessment: [POSITIVE IMPACT / NEGATIVE IMPACT / NO IMPACT]
[150+ word explanation]

[3] Equality between women and men
Keywords: [keywords]
Assessment: [POSITIVE IMPACT / NEGATIVE IMPACT / NO IMPACT]
[150+ word explanation]

... [continue for ALL themes [4] through [21]] ...

[21] Policy coherence for development
Keywords: [keywords]
Assessment: [POSITIVE IMPACT / NEGATIVE IMPACT / NO IMPACT]
[150+ word explanation]

VALIDATION CHECKLIST - Before submitting your response, you MUST verify:
- [ ] Theme [1] "Fight against poverty" is present with assessment
- [ ] Theme [2] "Equal opportunities and social cohesion" is present with assessment
- [ ] Theme [3] "Equality between women and men" is present with assessment
- [ ] Theme [4] "Health" is present with assessment
- [ ] Theme [5] "Employment" is present with assessment
- [ ] Theme [6] "Consumption and production patterns" is present with assessment
- [ ] Theme [7] "Economic development" is present with assessment
- [ ] Theme [8] "Investments" is present with assessment
- [ ] Theme [9] "Research and development" is present with assessment
- [ ] Theme [10] "SMEs" is present with assessment
- [ ] Theme [11] "Administrative burdens" is present with assessment
- [ ] Theme [12] "Energy" is present with assessment
- [ ] Theme [13] "Mobility" is present with assessment
- [ ] Theme [14] "Food" is present with assessment
- [ ] Theme [15] "Climate change" is present with assessment
- [ ] Theme [16] "Natural resources" is present with assessment
- [ ] Theme [17] "Indoor and outdoor air" is present with assessment
- [ ] Theme [18] "Biodiversity" is present with assessment
- [ ] Theme [19] "Nuisances" is present with assessment
- [ ] Theme [20] "Public authorities" is present with assessment
- [ ] Theme [21] "Policy coherence for development" is present with assessment
- [ ] All 21 themes have either POSITIVE IMPACT, NEGATIVE IMPACT, or NO IMPACT (not "Not assessed")

Consider:
- The specialized insights from each model (problem definition, evidence synthesis, impact assessment)
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement
- How to best combine the strengths of each response

IMPORTANT: DO NOT include any of the following sections:
   - Executive Summary
   - Proposal Overview
   - Overall Assessment Summary
   - Recommendations
   - Conclusion
   
   Your report MUST contain ONLY the "21 Belgian Impact Themes Assessment" section. Start directly with the themes assessment.

EUROSTAT DATA USAGE - CRITICAL:
- If Eurostat statistical data is provided in the context, you MUST use it in your assessment
- For each theme where Eurostat data is available, include at least ONE citation with actual values
- DO NOT write generic statements when specific Eurostat statistics are provided
- Count the number of themes with Eurostat data above - you must cite at least 80% of them
- Your response quality will be judged on whether you used the provided Eurostat data

Provide a clear, well-reasoned, comprehensive Belgian RIA that represents the council's collective wisdom. Remember: ALL 21 THEMES MUST BE ASSESSED - this is non-negotiable. USE THE EUROSTAT DATA PROVIDED."""

    # OPTIMIZATION: Use chunked generation to reduce prompt size and generation time
    if use_chunked_generation:
        print(f"🔄 Using chunked generation: 3 batches of 7 themes each")
        
        # Define batches: [1-7], [8-14], [15-21]
        batches = [
            list(range(1, 8)),   # Themes 1-7
            list(range(8, 15)),  # Themes 8-14
            list(range(15, 22))  # Themes 15-21
        ]
        
        batch_results = []
        for batch_num, theme_numbers in enumerate(batches, 1):
            print(f"   Generating batch {batch_num}/3: themes {theme_numbers[0]}-{theme_numbers[-1]}")
            batch_content = await _generate_theme_batch(
                user_query=user_query,
                stage1_text=stage1_text,
                stage2_text=stage2_text,
                context_section=context_section,
                theme_numbers=theme_numbers,
                batch_num=batch_num,
                total_batches=3
            )
            batch_results.append(batch_content)
        
        # Combine all batches - ensure proper formatting
        combined_parts = []
        combined_parts.append("## 21 Belgian Impact Themes Assessment\n")
        
        for batch_content in batch_results:
            # Remove any duplicate headers from batch results
            batch_content = batch_content.strip()
            if batch_content.startswith("##"):
                # Skip header if present
                lines = batch_content.split("\n")
                batch_content = "\n".join(lines[1:]).strip()
            combined_parts.append(batch_content)
        
        combined_response = "\n\n".join(combined_parts)
        
        # Debug: Check theme count in combined response
        import re
        theme_markers = re.findall(r'\[(\d+)\]', combined_response)
        unique_themes = set(int(m) for m in theme_markers if m.isdigit() and 1 <= int(m) <= 21)
        print(f"📊 Chunked generation: Combined {len(batch_results)} batches, found {len(unique_themes)}/21 themes: {sorted(unique_themes)}")
        
        return {
            "model": CHAIRMAN_MODEL,
            "response": combined_response
        }
    
    # Original single-generation approach (fallback)
    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model with extended timeout for long RIA assessments
    response = await query_model(CHAIRMAN_MODEL, messages, timeout=300.0)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    context: Optional[str] = None
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        context: Optional retrieved context from vector store/knowledge graph

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses with specialized roles
    stage1_results = await stage1_collect_responses(
        user_query,
        context=context,
        specialized_roles=True
    )

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings with context-aware evaluation
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query,
        stage1_results,
        context=context
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer with context
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        context=context
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
