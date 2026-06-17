"""
NiFiPilot Monitor Agent
-----------------------
Read-only sub-agent specialized in NiFi health checks,
flow inspection and queue monitoring.

Uses Claude API + NiFiPilot MCP tools via SSE.
"""

import asyncio
import json
import os
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from mcp.client.sse import sse_client
from mcp import ClientSession

load_dotenv()

MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/sse")

SYSTEM_PROMPT = """
You are a NiFi monitoring specialist with access to NiFiPilot MCP tools.
Your role is READ-ONLY: inspect, diagnose and report. Never modify anything.

Follow the NiFiPilot Agent Skill rules:
1. Always start with get_system_diagnostics
2. Then get_process_groups to understand structure
3. Use get_flow_status and get_connections to find issues
4. Report findings clearly with health indicators (✅ ⚠️ ❌)
5. Suggest fixes but never execute them — that is the ops agent's job

Response format:
- Start with overall health summary
- List any issues found
- Suggest next steps
"""

TOOLS = [
    {
        "name": "get_system_diagnostics",
        "description": "Get NiFi system health: heap, CPU, JVM version, uptime.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_process_groups",
        "description": "List direct child process groups of group_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "default": "root"}
            }
        }
    },
    {
        "name": "get_processors",
        "description": "List all processors in group_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "default": "root"}
            }
        }
    },
    {
        "name": "get_flow_status",
        "description": "Get running/stopped/invalid counts for a process group.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "default": "root"}
            }
        }
    },
    {
        "name": "get_connections",
        "description": "List all connections with queue depth in group_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "default": "root"}
            }
        }
    },
    {
        "name": "get_queue_status",
        "description": "Get current queue depth for a specific connection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "connection_id": {"type": "string"}
            },
            "required": ["connection_id"]
        }
    }
]


async def run_monitor_agent(user_message: str) -> str:
    """Run the monitor agent with a user message."""
    client = AsyncAnthropic()

    skill_path = os.path.join(os.path.dirname(__file__),
                              "../../skills/nifipilot-agent.md")
    skill_content = ""
    if os.path.exists(skill_path):
        with open(skill_path, "r") as f:
            skill_content = f.read()

    messages = [
        {
            "role": "user",
            "content": f"{user_message}\n\n---\nSkill reference:\n{skill_content}"
        }
    ]

    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            while True:
                response = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages
                )

                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            return block.text
                    return "No response generated."

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  🔧 Calling {block.name}({json.dumps(block.input)})")
                        result = await session.call_tool(block.name, block.input)
                        parts = [
                            item.text if hasattr(item, "text") else str(item)
                            for item in result.content
                        ]
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "\n".join(parts) if parts else "No output"
                        })

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    print("NiFiPilot Monitor Agent")
    print("=" * 40)
    result = asyncio.run(run_monitor_agent(
        "Check the current state of NiFi and report any issues."
    ))
    print(result)
