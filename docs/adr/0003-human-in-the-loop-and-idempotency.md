# ADR-0003: Human-in-the-Loop Interrupts & Idempotent Side Effects

## Context
Customer service agents perform actions with real financial and legal ramifications (e.g., money refunds, address rerouting). Fully autonomous systems risk prompt injections, policy hallucinations, or unintended financial loss (OWASP LLM06: Excessive Agency).

## Decision
1. **LangGraph `interrupt()`**:
   - For high-risk actions (e.g., refund amounts > \$50, order cancellations for orders in fulfillment, manual exception overrides), the graph pauses execution and enters an `awaiting_approval` state.
2. **Reviewer Console**:
   - Human operators inspect the pending action, supporting evidence from the conversation, and diff in the reviewer console UI.
   - Operations include: `APPROVE`, `EDIT` (modify parameters, e.g. reduce refund amount), or `REJECT` (with reviewer rationale).
3. **Idempotency Safeguard**:
   - When a node resumes after an `interrupt()`, LangGraph may re-run the node. To prevent duplicate charges or double refunds, all side-effecting operations require an `idempotency_key` (UUID derived from ticket and action ID) enforced at the service database layer.

## Consequences
- **Positive**: Zero unauthorized high-value transactions; satisfies enterprise compliance and risk governance.
- **Negative**: Asynchronous pause requires checkpointer persistence and UI notification mechanism.
