"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
# These models participate in Stage 1 (first-opinion generation) and Stage 2 (peer review)
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "x-ai/grok-4",
    # Note: Claude Sonnet 4.5 moved to Meta-Chairman role (see below)
]

# Meta-Chairman model - synthesizes final response
# IMPORTANT: This model must NOT be in COUNCIL_MODELS
# The Meta-Chairman does NOT participate in Stage 1 or Stage 2
# It only sees the complete deliberation record and produces the final synthesis
# 
# Recommended Meta-Chairman models (prioritize judgment and synthesis):
# - "anthropic/claude-sonnet-4.5" - Excellent at synthesis, conflict resolution, balanced judgment
# - "anthropic/claude-opus-4" - Strong reasoning and synthesis capabilities
# - "openai/gpt-4o" - Good at balanced analysis and synthesis
# - "google/gemini-2.0-flash-exp" - Fast and capable synthesis
CHAIRMAN_MODEL = "anthropic/claude-sonnet-4.5"

# Validation: Ensure Meta-Chairman is not in the council
if CHAIRMAN_MODEL in COUNCIL_MODELS:
    raise ValueError(
        f"Meta-Chairman model '{CHAIRMAN_MODEL}' cannot be in COUNCIL_MODELS. "
        "The Meta-Chairman must be a separate model that does not participate "
        "in Stage 1 (first-opinion generation) or Stage 2 (peer review)."
    )

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Bootstrap evaluation contexts configuration
# This reduces pattern recognition bias by varying evaluation contexts
# while maintaining semantic coherence of responses

# Number of bootstrap iterations for Stage 2 evaluation
# Recommended: 5 iterations (good balance of bias reduction vs. cost)
# Minimum: 3 iterations, Optimal: 7-10 iterations
BOOTSTRAP_ITERATIONS = 5

# Enable bootstrap evaluation contexts (set to False to use original single evaluation)
ENABLE_BOOTSTRAP_EVALUATION = True

# Evaluation criteria variations for bootstrap
# Each criterion focuses on a different aspect of response quality
EVALUATION_CRITERIA = [
    {
        "name": "accuracy",
        "focus": "technical accuracy and correctness",
        "description": "Rank based on factual correctness, technical accuracy, and absence of errors"
    },
    {
        "name": "completeness",
        "focus": "completeness and comprehensiveness",
        "description": "Rank based on coverage of all relevant aspects, depth of explanation, and comprehensiveness"
    },
    {
        "name": "clarity",
        "focus": "clarity and accessibility",
        "description": "Rank based on clarity of explanation, ease of understanding, and effective communication"
    },
    {
        "name": "utility",
        "focus": "practical usefulness",
        "description": "Rank based on actionable insights, practical applicability, and real-world usefulness"
    },
    {
        "name": "balanced",
        "focus": "overall quality",
        "description": "Rank holistically considering all factors: accuracy, completeness, clarity, and utility"
    }
]

# Aggregation method for bootstrap rankings
# Options: "borda_count", "position_average", "consensus_score", "weighted_consensus"
BOOTSTRAP_AGGREGATION_METHOD = "borda_count"
