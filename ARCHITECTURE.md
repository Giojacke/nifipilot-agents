# Architecture — NiFiPilot Agents

## C1 — System Context

```mermaid
graph TD
    User(["👤 User / Developer"])
    Claude["🤖 AI Model<br/>(Claude / GPT-4 / Llama / Gemini)"]
    Agents["NiFiPilot Agents<br/>(this repo)"]
    MCP["NiFiPilot MCP Server<br/>(pip install nifipilot)"]
    NiFi["Apache NiFi 2.x<br/>(localhost:8443)"]

    User -->|"natural language request"| Agents
    Agents -->|"LiteLLM API call"| Claude
    Claude -->|"tool calls"| Agents
    Agents -->|"MCP SSE connection"| MCP
    MCP -->|"REST API"| NiFi
    NiFi -->|"JSON response"| MCP
    MCP -->|"tool result"| Agents
    Agents -->|"final report"| User

    style Agents fill:#0A1628,color:#fff,stroke:#1D9E75
    style MCP fill:#085041,color:#fff,stroke:#1D9E75
    style NiFi fill:#0C447C,color:#fff,stroke:#185FA5
    style Claude fill:#3C3489,color:#fff,stroke:#534AB7
    style User fill:#2C2C2A,color:#fff,stroke:#5F5E5A
```

---

## C2 — Container Diagram

```mermaid
graph TD
    subgraph agents_repo["nifipilot-agents (this repo)"]
        Supervisor["nifi_supervisor.py<br/>Orchestrator"]
        Monitor["monitor_agent.py<br/>Read-only"]
        Builder["builder_agent.py<br/>Creates flows"]
        Ops["ops_agent.py<br/>Start/Stop/Control"]
        Skill["skills/nifipilot-agent.md<br/>Agent instructions"]
        LiteLLM["LiteLLM<br/>Multi-provider abstraction"]
    end

    subgraph mcp_repo["mcp-nifipilot (separate repo)"]
        MCPServer["nifi-mcp<br/>FastMCP SSE server"]
        Tools["17 MCP Tools<br/>read / write / control"]
    end

    subgraph nifi["Apache NiFi 2.x"]
        RESTAPI["REST API :8443"]
    end

    subgraph providers["AI Providers (choose one)"]
        Claude["Claude API"]
        OpenAI["OpenAI API"]
        Ollama["Ollama (local/free)"]
        Gemini["Gemini API"]
    end

    Supervisor --> Monitor
    Supervisor --> Builder
    Supervisor --> Ops
    Monitor --> Skill
    Builder --> Skill
    Ops --> Skill
    Monitor --> LiteLLM
    Builder --> LiteLLM
    Ops --> LiteLLM
    LiteLLM --> Claude
    LiteLLM --> OpenAI
    LiteLLM --> Ollama
    LiteLLM --> Gemini
    Monitor -->|"SSE :8000"| MCPServer
    Builder -->|"SSE :8000"| MCPServer
    Ops -->|"SSE :8000"| MCPServer
    MCPServer --> Tools
    Tools -->|"HTTPS REST"| RESTAPI

    style Supervisor fill:#0A1628,color:#fff,stroke:#1D9E75
    style Monitor fill:#085041,color:#fff,stroke:#1D9E75
    style Builder fill:#085041,color:#fff,stroke:#1D9E75
    style Ops fill:#085041,color:#fff,stroke:#1D9E75
    style MCPServer fill:#085041,color:#fff,stroke:#1D9E75
    style LiteLLM fill:#712B13,color:#fff,stroke:#993C1D
    style Ollama fill:#2C2C2A,color:#fff,stroke:#5F5E5A
```

---

## C3 — Component Diagram (Monitor Agent internals)

```mermaid
graph TD
    subgraph monitor["monitor_agent.py"]
        Entry["run_monitor_agent(user_message)"]
        LoadSkill["Load skills/nifipilot-agent.md"]
        BuildMessages["Build messages list<br/>(system + user + skill)"]
        LiteLLMCall["litellm.acompletion()<br/>model from LITELLM_MODEL env var"]
        CheckStop{"tool_calls?"}
        ExtractText["Extract text response"]
        ProcessTools["Process tool calls"]
        CallMCP["session.call_tool(name, input)"]
        AppendResults["Append tool results to messages"]
        Return["Return final response"]
    end

    subgraph mcp_session["MCP Session (SSE)"]
        SSEConnect["sse_client(MCP_URL)"]
        MCPInit["session.initialize()"]
        ToolCall["session.call_tool()"]
    end

    Entry --> LoadSkill
    LoadSkill --> BuildMessages
    BuildMessages --> LiteLLMCall
    LiteLLMCall --> CheckStop
    CheckStop -->|"No → end_turn"| ExtractText
    CheckStop -->|"Yes → has tool calls"| ProcessTools
    ProcessTools --> CallMCP
    CallMCP --> SSEConnect
    SSEConnect --> MCPInit
    MCPInit --> ToolCall
    ToolCall --> AppendResults
    AppendResults --> LiteLLMCall
    ExtractText --> Return

    style Entry fill:#0A1628,color:#fff,stroke:#1D9E75
    style LiteLLMCall fill:#712B13,color:#fff,stroke:#993C1D
    style CallMCP fill:#085041,color:#fff,stroke:#1D9E75
    style CheckStop fill:#2C2C2A,color:#fff,stroke:#5F5E5A
```

---

## Design Decisions

### ADR-001 — LiteLLM over direct SDK

**Decision:** Use LiteLLM as the AI provider abstraction layer instead of calling Anthropic, OpenAI or other SDKs directly.

**Why:** NiFiPilot Agents should work with any AI model — Claude, GPT-4, Gemini, local Ollama models, DeepSeek, etc. LiteLLM provides a unified OpenAI-compatible interface for all providers with a single line change in `.env`.

**Trade-off:** LiteLLM adds one dependency and a thin abstraction layer. Accepted because provider flexibility outweighs this cost.

---

### ADR-002 — SSE connection per agent run

**Decision:** Open one SSE connection to the NiFiPilot MCP server per agent invocation and keep it open for the entire agentic loop.

**Why:** Opening and closing the SSE connection on every tool call would add significant latency. Keeping one session open for the duration of the loop is more efficient and matches how MCP clients like Claude Code work.

---

### ADR-003 — Skill-based instruction set

**Decision:** Agent behavior is defined in `skills/nifipilot-agent.md`, not hardcoded in the system prompt alone.

**Why:** The skill file can be updated, versioned and shared across agents without changing code. It also allows users to customize agent behavior by editing the markdown file. The system prompt contains the role definition; the skill contains the operational rules.

---

### ADR-004 — Specialized sub-agents over one monolithic agent

**Decision:** Separate agents for monitoring, building and operations instead of one agent that does everything.

**Why:** Specialized agents are easier to test, safer (monitor agent is read-only by design), and easier to reason about. The supervisor orchestrates them for complex tasks.

---

## Roadmap

- [x] Monitor Agent with LiteLLM + MCP SSE
- [ ] Builder Agent — create flows from natural language
- [ ] Ops Agent — start/stop/control operations  
- [ ] Supervisor Agent — orchestrate sub-agents
- [ ] Grafana MCP integration — query dashboards
- [ ] Loki MCP integration — search NiFi logs
- [ ] Observability Agent — correlate metrics with flow events
