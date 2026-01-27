"""Configuration for the LLM Council."""

import os

# Load .env file FIRST before importing anything else
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, PermissionError, FileNotFoundError):
    pass

# Import API keys from centralized module
try:
    from .api_keys import (
        ANTHROPIC_API_KEY,
        GOOGLE_API_KEY,
        XAI_API_KEY,
        OPENAI_API_KEY,
        OPENROUTER_API_KEY
    )
except ImportError:
    # Fallback to direct environment access
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    XAI_API_KEY = os.getenv("XAI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Use direct APIs if available, otherwise fallback to OpenRouter
USE_DIRECT_APIS = bool(ANTHROPIC_API_KEY or GOOGLE_API_KEY or XAI_API_KEY or OPENAI_API_KEY)

# Council members - list of model identifiers
# These models participate in Stage 1 (first-opinion generation) and Stage 2 (peer review)
# If using direct APIs, these will be called directly; otherwise via OpenRouter
COUNCIL_MODELS = [
    "google/gemini-2.0-flash-exp",  # Evidence synthesis specialist
    "x-ai/grok-2-1212",  # Impact assessment specialist
    "openai/gpt-4",  # General analysis specialist (using OpenAI directly)
    # Fallback models if direct APIs not available:
    # "openai/gpt-5.1",
    # "google/gemini-3-pro-preview",
    # "x-ai/grok-4",
]

# Meta-Chairman model - synthesizes final response
# IMPORTANT: This model must NOT be in COUNCIL_MODELS
# The Meta-Chairman does NOT participate in Stage 1 or Stage 2
# It only sees the complete deliberation record and produces the final synthesis
# 
# Recommended Meta-Chairman models (prioritize judgment and synthesis):
# - "anthropic/claude-sonnet-4-20250514" - Excellent at synthesis, conflict resolution, balanced judgment
# - "anthropic/claude-opus-4" - Strong reasoning and synthesis capabilities
# - "openai/gpt-4o" - Good at balanced analysis and synthesis
CHAIRMAN_MODEL = "anthropic/claude-sonnet-4-20250514"

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
# Recommended: 3 iterations (reduced from 5 to reduce API load and token usage)
# Minimum: 3 iterations, Optimal: 7-10 iterations (but heavy on API calls)
# Note: Reduced to 3 to avoid token limit issues and reduce API costs
BOOTSTRAP_ITERATIONS = 3

# Enable bootstrap evaluation contexts (set to False to use original single evaluation)
# Disabled to reduce API load and token usage - using single evaluation instead
ENABLE_BOOTSTRAP_EVALUATION = False

# Evaluation criteria variations for bootstrap
# RIA-specific criteria for evaluating impact assessments
EVALUATION_CRITERIA = [
    {
        "name": "ria_structure",
        "focus": "Belgian RIA structure compliance",
        "description": "Rank based on adherence to Belgian RIA structure (21 themes), proper section organization, and format compliance"
    },
    {
        "name": "analysis_depth",
        "focus": "EU-style analysis depth",
        "description": "Rank based on evidence-based reasoning, comprehensive analysis, domain-specific insights, and analytical rigor"
    },
    {
        "name": "context_usage",
        "focus": "retrieved context utilization",
        "description": "Rank based on effective use of retrieved EU and Belgian RIA documents, proper citations, and reference to analysis patterns"
    },
    {
        "name": "completeness",
        "focus": "completeness of assessment",
        "description": "Rank based on coverage of all 21 impact themes, comprehensive Executive Summary and Proposal Overview, and thorough impact assessments"
    },
    {
        "name": "balanced",
        "focus": "overall RIA quality",
        "description": "Rank holistically considering structure, analysis depth, context usage, and completeness for Belgian RIA standards"
    }
]

# Aggregation method for bootstrap rankings
# Options: "borda_count", "position_average", "consensus_score", "weighted_consensus"
BOOTSTRAP_AGGREGATION_METHOD = "borda_count"
