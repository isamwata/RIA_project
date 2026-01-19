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

# Import API clients - prefer direct APIs, fallback to OpenRouter
if USE_DIRECT_APIS:
    try:
        from .direct_apis import query_models_parallel_direct as query_models_parallel, query_model_direct as query_model
        print("✅ Using direct APIs (Anthropic, Google, xAI, OpenAI)")
    except ImportError:
        from .openrouter import query_models_parallel, query_model
        print("⚠️  Direct APIs not available, using OpenRouter")
else:
    from .openrouter import query_models_parallel, query_model
    print("⚠️  Using OpenRouter (direct API keys not found)")


async def stage1_collect_responses(
    user_query: str,
    context: Optional[str] = None,
    specialized_roles: bool = True
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.
    
    For RIA generation, models are assigned specialized roles:
    - Claude: Problem definition and policy analysis specialist
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
                # OpenAI: Problem definition and general analysis specialist
                specialized_queries[model] = f"""{user_query}

You are a Problem Definition and Policy Analysis Specialist. Focus on:
- Comprehensive problem definition and background
- Policy context and regulatory gaps
- Drawing insights from retrieved EU Impact Assessment documents

Retrieved Context:
{context[:2000] if len(context) > 2000 else context}

Generate a detailed Background/Problem Definition section and overall assessment structure."""
        
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
   - Completeness of Background/Problem Definition section
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


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    context: Optional[str] = None
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
        context_section = f"""

RETRIEVED CONTEXT (from EU and Belgian RIA documents):
{context[:3000] if len(context) > 3000 else context}

Use this context to ensure your synthesis:
- References specific documents where appropriate (e.g., SWD(2022) 167 final)
- Uses similar analysis patterns from retrieved EU documents
- Maintains consistency with Belgian RIA structure"""

    chairman_prompt = f"""You are the Meta-Chairman of an LLM Council for Belgian Regulatory Impact Assessment generation. Multiple AI models have provided specialized responses, and then ranked each other's responses.

Original Query: {user_query}
{context_section}

STAGE 1 - Individual Responses (from specialized models):
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Meta-Chairman is to synthesize all of this information into a single, comprehensive Belgian RIA assessment. 

CRITICAL REQUIREMENTS:
1. Structure: Background/Problem Definition (FIRST), Executive Summary, Proposal Overview, 21 Impact Themes Assessment, Overall Assessment Summary, Recommendations
2. Use retrieved context: Reference specific EU documents (SWD, COM references) and Belgian RIA examples where relevant
3. Citations: Include citations when referencing analysis patterns or methodologies from retrieved documents
4. Completeness: Ensure all 21 impact themes are assessed with clear positive/negative/no impact determinations
5. Quality: Use EU-style detailed, evidence-based analysis while maintaining Belgian RIA form structure

Consider:
- The specialized insights from each model (problem definition, evidence synthesis, impact assessment)
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement
- How to best combine the strengths of each response

Provide a clear, well-reasoned, comprehensive Belgian RIA that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

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
