# NiFiPilot Agents

AI agents that control Apache NiFi via natural language using the NiFiPilot MCP server.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![NiFiPilot](https://img.shields.io/badge/powered%20by-NiFiPilot-blue)](https://github.com/Giojacke/mcp-nifipilot)

---

## What is this

NiFiPilot Agents is an orchestration layer that lets any AI model control Apache NiFi flows via the NiFiPilot MCP server.

- **Provider-agnostic** — works with Claude, GPT-4, Gemini, Llama, DeepSeek and any LiteLLM-compatible model
- **Multi-agent** — specialized sub-agents for monitoring, building and operations
- **Skill-based** — agents follow the NiFiPilot Agent Skill for safe, consistent behavior
- **Free to develop** — use Ollama locally with no API costs

---

## Architecture

```
User request
     ↓
NiFi Supervisor Agent (orchestrator)
     ↓
┌────────────────────────────────────┐
│  Monitor Agent  │  Builder Agent   │
│  (read-only)    │  (creates flows) │
├────────────────────────────────────┤
│         Ops Agent                  │
│  (start/stop/control)              │
└────────────────────────────────────┘
     ↓
NiFiPilot MCP Server (pip install nifipilot)
     ↓
Apache NiFi 2.x REST API
```

---

## Quick start

### 1. Install NiFiPilot MCP server

```bash
pip install nifipilot
```

Start the MCP server (or use Docker Compose from the NiFiPilot repo):

```bash
NIFI_URL=https://localhost:8443 \
NIFI_USERNAME=admin \
NIFI_PASSWORD=your-password \
MCP_MODE=full \
nifi-mcp
```

### 2. Install NiFiPilot Agents

```bash
git clone https://github.com/Giojacke/nifipilot-agents
cd nifipilot-agents
pip install -e .
```

### 3. Configure your AI provider

```bash
cp .env.example .env
```

Edit `.env` and choose your provider:

```env
# Option A — Anthropic Claude (recommended)
LITELLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=your-key

# Option B — OpenAI
# LITELLM_MODEL=gpt-4o
# OPENAI_API_KEY=your-key

# Option C — Ollama (free, local, no API key needed)
# LITELLM_MODEL=ollama/llama3.2
```

### 4. Run the monitor agent

```bash
python agents/sub_agents/monitor_agent.py
```

---

## Agents

### Monitor Agent (available now)
Read-only agent specialized in NiFi health checks and diagnostics.

```bash
python agents/sub_agents/monitor_agent.py
```

**Capabilities:**
- System health check (heap, CPU, uptime)
- Flow status inspection
- Queue depth monitoring
- Issue detection and reporting

### Builder Agent (coming soon)
Creates NiFi flows from natural language descriptions.

### Ops Agent (coming soon)
Controls start/stop/control operations on NiFi flows.

### Supervisor Agent (coming soon)
Orchestrates sub-agents for complex multi-step tasks.

---

## Supported AI providers

| Provider | Model example | Cost |
|----------|--------------|------|
| Anthropic | claude-sonnet-4-6 | ~$3/M tokens |
| Anthropic | claude-haiku-4-5 | ~$0.25/M tokens |
| OpenAI | gpt-4o | ~$5/M tokens |
| Google | gemini/gemini-pro | Free tier available |
| Ollama | ollama/llama3.2 | Free (local) |
| DeepSeek | deepseek/deepseek-chat | ~$0.14/M tokens |

---

## Using the Agent Skill

The `skills/nifipilot-agent.md` file contains the instruction set that guides agents to use NiFiPilot tools safely.

To use it with any AI:

**Claude Code:**
```
Read skills/nifipilot-agent.md and use it as your instruction set.
Then check the current state of NiFi.
```

**VS Code / Cursor:**
Pin `skills/nifipilot-agent.md` to the chat context before starting a NiFi session.

---

## Cost control

For development, use Ollama (free):

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.2

# In .env:
LITELLM_MODEL=ollama/llama3.2
```

For production, set a spending limit:
- Anthropic: https://console.anthropic.com/settings/limits
- OpenAI: https://platform.openai.com/settings/organization/limits

---

## Requirements

- Python 3.11+
- NiFiPilot MCP server running (`pip install nifipilot`)
- Apache NiFi 2.x instance
- One of: Anthropic API key, OpenAI API key, or Ollama installed

---

## Related projects

- [NiFiPilot MCP Server](https://github.com/Giojacke/mcp-nifipilot) — the MCP server this agent uses
- [NiFiPilot on PyPI](https://pypi.org/project/nifipilot/) — `pip install nifipilot`
- [NiFiPilot VS Code Extension](https://marketplace.visualstudio.com/items?itemName=CodHector.nifipilot)

---

## License

MIT

---

## Author

Built by [CodHector](https://github.com/Giojacke) 🤙
