# NiFiPilot Agents

## What is this
Orchestration agents that use NiFiPilot MCP server to automate
Apache NiFi flow management via natural language.

This repo contains:
- A supervisor agent that orchestrates sub-agents
- Sub-agents specialized in monitoring, building and operations
- Examples and usage guides

## Stack
- Python 3.11+
- anthropic (Claude API direct)
- nifipilot (MCP server — pip install nifipilot)
- python-dotenv

## Architecture
agents/
  nifi_supervisor.py     # Main orchestrator agent
  sub_agents/
    monitor_agent.py     # Read-only: diagnostics and health checks
    builder_agent.py     # Creates flows from natural language
    ops_agent.py         # Start/stop/control operations

skills/                  # Copy of nifipilot skills
examples/                # Usage examples

## Rules
- Agents always use the NiFiPilot skill from skills/nifipilot-agent.md
- Never hardcode credentials — use .env
- Sub-agents are specialized — never mix responsibilities
- Supervisor coordinates, sub-agents execute

## How to start a session
"Read CLAUDE.md and the skill in skills/nifipilot-agent.md, 
then tell me what agents are available and what they can do."

## Progress
<!-- Claude updates this section at end of each session -->
- Session 1: repo created, CLAUDE.md defined, architecture planned
