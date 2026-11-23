# Service Level Objectives (SLOs) & Operational Runbook

## 1. Service Level Objectives (SLOs)

| Metric | Target | Measurement Method | Current Benchmark |
| :--- | :--- | :--- | :--- |
| **Availability** | $\ge 99.9\%$ | Uptime of FastAPI & Streamlit endpoints | 100% in local test runs |
| **P95 Turn Latency** | $< 15.0\text{s}$ | End-to-end multi-agent pipeline (Triage $\to$ Specialist $\to$ Resolution) | **10.64s** (`RUN-002`) |
| **Single-turn Latency (Triage)** | $< 1.5\text{s}$ | Fast triage node execution | **~0.8s** on Groq LPU |
| **Unauthorized Action Rate** | **$0.0\%$** | Adversarial test suite runs (SCEN-13, SCEN-14) | **0.0%** (100% blocked) |
| **pass^k Consistency** | $\ge 80\%$ | Scenario success consistency across $k=3$ runs | Measured in `docs/lab-notes.md` |

---

## 2. On-Call Incident Runbook

### Incident 1: Graph Halted on High-Value Refund
- **Symptom**: Ticket state has `is_paused = True` and next node is `human_approval_gate`.
- **Root Cause**: Normal behavior for refunds exceeding $50.00.
- **Action**: Open the Reviewer Console (`apps/reviewer_ui.py`), inspect the order history and customer complaint, and click **Approve** or **Reject**.

### Incident 2: SQLite Checkpoint Lock (`database is locked`)
- **Symptom**: Worker fails to write new checkpoint state.
- **Root Cause**: Unclosed database connections holding write locks.
- **Remediation**:
  1. Ensure all service connections use context managers (`with get_connection() as conn:`).
  2. In production, migrate from local SQLite to PostgreSQL checkpointer (`langgraph-checkpoint-postgres`).

### Incident 3: LLM Provider Timeout or Rate Limit
- **Symptom**: `groq.RateLimitError` or HTTP 429.
- **Remediation**:
  1. The system utilizes `max_retries=2` with exponential backoff in `libs/models.py`.
  2. If the primary provider degrades, toggle `MODEL_PROVIDER=gemini` in `.env` to engage the fallback provider without changing graph logic.
