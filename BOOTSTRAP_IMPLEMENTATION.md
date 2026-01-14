# Bootstrap Evaluation Contexts Implementation

## Overview

The codebase has been updated to implement **bootstrap evaluation contexts** for Stage 2 ranking, which reduces pattern recognition bias while maintaining semantic coherence of responses.

## Changes Made

### 1. Configuration (`backend/config.py`)

Added new configuration parameters:

- **`BOOTSTRAP_ITERATIONS`**: Number of bootstrap iterations (default: 5)
- **`ENABLE_BOOTSTRAP_EVALUATION`**: Toggle to enable/disable bootstrap (default: True)
- **`EVALUATION_CRITERIA`**: List of evaluation criteria variations:
  - `accuracy`: Technical accuracy and correctness
  - `completeness`: Coverage and comprehensiveness
  - `clarity`: Clarity and accessibility
  - `utility`: Practical usefulness
  - `balanced`: Overall quality (holistic)
- **`BOOTSTRAP_AGGREGATION_METHOD`**: Method for aggregating rankings:
  - `borda_count`: Borda Count method (default)
  - `position_average`: Average position method
  - `consensus_score`: Consensus scoring method

### 2. Council Implementation (`backend/council.py`)

#### New Helper Functions

1. **`_generate_evaluation_prompt()`**: Generates evaluation prompts based on specific criteria
2. **`_shuffle_responses_order()`**: Randomizes response presentation order
3. **`_aggregate_bootstrap_rankings_borda()`**: Borda Count aggregation
4. **`_aggregate_bootstrap_rankings_position_average()`**: Position averaging aggregation
5. **`_aggregate_bootstrap_rankings_consensus_score()`**: Consensus scoring aggregation

#### Updated `stage2_collect_rankings()`

The function now:

1. **Creates Bootstrap Iterations**: Runs multiple evaluation rounds (default: 5)
2. **Varies Evaluation Criteria**: Each iteration uses a different criterion (accuracy, completeness, clarity, utility, balanced)
3. **Varies Response Order**: Randomizes the order of responses in each iteration
4. **Aggregates Rankings**: Combines rankings across iterations using the configured method
5. **Maintains Backward Compatibility**: Falls back to original method if `ENABLE_BOOTSTRAP_EVALUATION = False`

## How It Works

### Bootstrap Process Flow

```
For each bootstrap iteration (1 to BOOTSTRAP_ITERATIONS):
  1. Select evaluation criterion (accuracy, completeness, clarity, utility, balanced)
  2. Shuffle response order (maintains semantic coherence)
  3. Generate criterion-specific evaluation prompt
  4. All council models evaluate in parallel
  5. Collect rankings with iteration metadata

After all iterations:
  1. Group rankings by model
  2. Aggregate rankings using configured method (Borda Count, etc.)
  3. Generate final consensus ranking per model
  4. Return aggregated results
```

### Example: 5 Iterations

**Iteration 1**: Accuracy criterion, Order [A, B, C]
- All models evaluate focusing on accuracy
- Rankings collected

**Iteration 2**: Completeness criterion, Order [B, C, A]
- All models evaluate focusing on completeness
- Different order tests robustness

**Iteration 3**: Clarity criterion, Order [C, A, B]
- All models evaluate focusing on clarity
- Different order again

**Iteration 4**: Utility criterion, Order [A, C, B]
- All models evaluate focusing on utility

**Iteration 5**: Balanced criterion, Order [B, A, C]
- All models evaluate holistically

**Aggregation**: All rankings combined using Borda Count (or selected method)

## Benefits

### 1. Reduces Pattern Recognition Bias
- Different criteria reveal different aspects
- Models can't rely on single pattern matching strategy
- Bias becomes inconsistent across iterations

### 2. Maintains Semantic Coherence
- All responses always present (no broken references)
- Full context preserved
- No semantic degradation

### 3. Tests Robustness
- If a response ranks well across diverse contexts, it's genuinely better
- Reduces bias from single evaluation perspective
- More reliable final rankings

### 4. Configurable
- Can adjust number of iterations
- Can choose aggregation method
- Can enable/disable bootstrap evaluation

## Configuration Examples

### Minimal Bootstrap (3 iterations)
```python
BOOTSTRAP_ITERATIONS = 3
ENABLE_BOOTSTRAP_EVALUATION = True
```

### Strong Bootstrap (7 iterations)
```python
BOOTSTRAP_ITERATIONS = 7
ENABLE_BOOTSTRAP_EVALUATION = True
```

### Disable Bootstrap (Original Method)
```python
ENABLE_BOOTSTRAP_EVALUATION = False
```

### Use Position Averaging
```python
BOOTSTRAP_AGGREGATION_METHOD = "position_average"
```

## Aggregation Methods Explained

### Borda Count (Default)
- 1st place gets N points, 2nd gets N-1, etc.
- Sums points across all iterations
- Higher total score = better ranking
- **Best for**: Rewarding consistent high rankings

### Position Average
- Averages position across iterations
- Lower average = better ranking
- **Best for**: Simple, intuitive aggregation

### Consensus Score
- Similar to Borda Count but emphasizes consistency
- Rewards responses that consistently rank high
- **Best for**: Detecting genuine quality vs. outliers

## Performance Considerations

### API Calls
- **Without Bootstrap**: N models × 1 iteration = N calls
- **With Bootstrap**: N models × K iterations = N×K calls
- **Example**: 3 models × 5 iterations = 15 calls (vs. 3 calls)

### Latency
- Bootstrap adds latency proportional to iterations
- All iterations run sequentially (could be parallelized in future)
- Trade-off: Higher latency for better bias reduction

### Cost
- Increases API costs proportionally
- 5 iterations = 5× cost for Stage 2
- Quality improvement usually worth the cost

## Backward Compatibility

The implementation maintains full backward compatibility:

- Set `ENABLE_BOOTSTRAP_EVALUATION = False` to use original method
- Original single-evaluation code path still available
- No breaking changes to function signatures
- Existing code continues to work

## Future Enhancements

Potential improvements:

1. **Parallel Bootstrap Iterations**: Run iterations in parallel to reduce latency
2. **Adaptive Iterations**: Adjust iterations based on consensus convergence
3. **Semantic Similarity Weighting**: Weight iterations based on criteria diversity
4. **Bias Detection**: Automatically detect and downweight biased rankings
5. **Custom Criteria**: Allow user-defined evaluation criteria

## Testing Recommendations

When testing the bootstrap implementation:

1. **Compare Results**: Run with and without bootstrap to see differences
2. **Check Consistency**: Verify rankings are more stable with bootstrap
3. **Monitor Costs**: Track API call increases
4. **Validate Aggregation**: Ensure aggregation methods work correctly
5. **Test Edge Cases**: Single response, two responses, many responses

## Summary

The bootstrap evaluation contexts implementation provides:

✅ **Bias Reduction**: Reduces pattern recognition bias through diverse evaluation contexts
✅ **Semantic Coherence**: Maintains full context (all responses always present)
✅ **Robustness**: Tests consistency across different criteria and orders
✅ **Configurability**: Flexible configuration options
✅ **Backward Compatibility**: Can be disabled to use original method

This implementation achieves the benefits of bootstrapping while respecting the semantic nature of LLM responses, making it ideal for the Meta-Chairman architecture.
