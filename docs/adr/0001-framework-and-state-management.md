# ADR-0001: LangGraph 1.x for State Management & Durable Checkpointing

## Context
Customer operations workflows require complex state management: multi-turn customer dialogues, branching based on order or customer status, tool execution, safety checks, and pauses for human reviews. Standard LLM chains or autonomous infinite-loop agents (like naive AutoGPT or basic ReAct scripts) are insufficient for enterprise production due to lack of determinism, memory crashes, and unpredictable loops.

## Decision
We select **LangGraph 1.x** as the primary orchestration engine with the following properties:
1. **Explicit Typed State**: All nodes read and mutate a strongly typed Pydantic/TypedDict state (`AgentState`) with custom reducers.
2. **Durable Execution via Checkpointers**: State is saved to a persistent checkpointer after every node execution. If a server restarts or a worker crashes, the ticket conversation resumes from the exact state.
3. **Supervisor-Specialist Topology**: A central supervisor coordinates specialist sub-agents, preventing cross-contamination of instructions and maintaining bounded context windows.

## Alternatives Considered
- **CrewAI**: High abstraction, good for role-playing, but lacks explicit low-level control over state transitions, cyclic state rollback, and durable database checkpointers.
- **Pure Custom Python Loops**: High maintenance overhead to re-implement graph routing, state reducers, and interrupt-resume mechanics.

## Consequences
- **Positive**: Complete observability over graph transitions; bulletproof crash recovery; clear boundaries between specialist agents.
- **Negative**: Requires learning LangGraph's state reduction patterns and graph compilation concepts.
