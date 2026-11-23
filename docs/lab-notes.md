# Experimentation & Evaluation Lab Notes

| Run ID | Date | Agent Architecture | Scenarios | Task Success (%) | pass^3 (%) | Tool Precision | Avg Latency (s) | Notes / Observations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RUN-001` | 2026-11-21 | Single ReAct Baseline | 20 | 100.0% (20/20) | *TODO* | 100% | ~3.20s | Fast single-turn baseline. Guardrails prevented prompt injections (SCEN-13, SCEN-14). Lacks durable state checkpointer, multi-agent separation of concerns, and native interrupt() UI. |
| `RUN-002` | 2026-11-21 | LangGraph Multi-Agent Supervisor | 20 | 100.0% (20/20) | *TODO* | 100% | 10.64s | Supervised graph (Triage -> Order/Billing or Policy -> Resolution) with SqliteSaver checkpointer. Marked improvement in empathy, structured receipts, and proactive assistance. |
| `RUN-003` | 2026-11-22 | Multi-Agent + HITL Interrupt (`interrupt()`) | 21 Unit Tests | 100.0% (21/21) | *TODO* | 100% | ~3.3s/test | Full Human-in-the-Loop lifecycle verified. High-value refunds ($180) pause execution with zero unauthorized DB writes; resumes via `Command(resume=...)` on approval/rejection. |

---

## Experiment Logs

### Run 001: Single ReAct Baseline Benchmark
- **Date**: 2026-11-21
- **Architecture**: `apps/baseline_agent.py` using `openai/gpt-oss-120b` via Groq.
- **Pass Rate**: 20 / 20 (100.0%)
- **Avg Latency**: 3.20s

### Run 002: LangGraph Multi-Agent Supervisor Architecture
- **Date**: 2026-11-21
- **Architecture**: `apps/graph.py` with typed `AgentState` and `SqliteSaver` checkpointer.
- **Pass Rate**: 20 / 20 (100.0%)
- **Avg Latency**: 10.64s

### Run 003: Human-in-the-Loop Interrupt Gate Verification
- **Date**: 2026-11-22
- **Architecture**: `apps/graph.py` with `human_approval_gate_node` calling `interrupt()`.
- **Test Suite**: `tests/test_hitl_approval.py` + full repository suite (21 unit & integration tests).
- **Results**: 21 / 21 Passed (100%).
- **Key Architectural Findings & Interview Ammo**:
  - **Durable Suspension**: When `issue_refund` is requested for $180, execution suspends. The checkpointer records `is_paused = True`.
  - **Zero Money-Movement while Paused**: Verified directly against the SQLite database: `payments.refunded_amount == 0.0`.
  - **Resumption with `Command(resume=...)`**: When human supervisor clicks Approve, the node re-activates, executes the database mutation, and delivers an approved receipt to the customer.
  - **Rejection Flow**: When supervisor clicks Reject with a reason, the record is marked `rejected`, payment is untouched, and the agent explains the policy refusal to the customer.
