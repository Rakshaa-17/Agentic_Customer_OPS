# ADR-0002: Decoupling Agent Tools using Model Context Protocol (MCP)

## Context
In tutorial agent systems, tools are typically standard Python functions bound directly into the model prompt. In enterprise customer operations:
1. Services (Orders, Payments, CRM) exist as independent microservices.
2. Direct function calling creates tight coupling, security hazards, and prevents cross-language or remote tool invocation.
3. The Agentic AI Foundation (Linux Foundation) has standardized **MCP** as the open standard for tool invocation.

## Decision
We implement tools as modular **MCP servers** (using FastMCP / Python MCP SDK):
- `orders-mcp`: Query orders, update shipping addresses, cancel unshipped orders.
- `payments-mcp`: Check payment records, process refunds (subject to authorization).
- `crm-mcp`: Fetch customer tiers, communication history, and issue loyalty credit.
- `knowledge-mcp`: Semantic retrieval of policy documents and refund rules.

Each agent in the graph is granted a scoped permission set (Least Privilege principle):
- The Policy Agent receives read-only access to `knowledge-mcp`.
- The Order & Billing Agent receives `orders-mcp` and `payments-mcp` access.

## Consequences
- **Positive**: Adheres to modern enterprise standards; tools can be independently tested, isolated, and containerized.
- **Negative**: Small IPC overhead compared to in-memory function calls (mitigated through local FastMCP transport in development).
