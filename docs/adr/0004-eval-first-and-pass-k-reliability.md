# ADR-0004: Eval-First Methodology, Deterministic Grading & pass^k

## Context
Testing agentic systems with traditional unit tests or simple string matching ("did the agent say 'refund approved'?") fails because LLM outputs are non-deterministic and can generate plausible-sounding lies while failing to execute the backend database mutations.

## Decision
1. **Eval-First Development**:
   - We construct a 20-scenario eval harness *before* engineering the complex multi-agent graph, scaling to 100+ scenarios before final release.
2. **Deterministic Database State Grading**:
   - Primary evaluation metric is ground-truth database state verification (e.g. check `payments_table` for exact balance change, check `orders_table` for status = 'cancelled').
3. **Two-Tier Evaluation**:
   - **Tier 1 (Deterministic)**: DB state diff, tool selection precision, argument correctness, policy gate adherence.
   - **Tier 2 (LLM Judge)**: Tone, empathy, clarity, policy phrasing accuracy.
4. **pass^k Metric**:
   - Every scenario runs $k=3$ times to compute consistency:
     $$\text{pass}^k = \frac{\text{scenarios passing all } k \text{ runs}}{\text{total scenarios}}$$

## Consequences
- **Positive**: Eliminates hallucinated progress; ensures reproducible benchmarks that can be published on resumes and READMEs.
- **Negative**: Requires running multiple simulated-user dialogues per evaluation cycle.
