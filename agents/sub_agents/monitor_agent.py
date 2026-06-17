"""
NiFiPilot Monitor Agent
-----------------------
Read-only sub-agent specialized in NiFi health checks,
flow inspection and queue monitoring.

Uses litellm (multi-provider) + NiFiPilot MCP tools via SSE.
"""

import asyncio
import json
import os
import litellm
from dotenv import load_dotenv
from mcp.client.sse import sse_client
from mcp import ClientSession

load_dotenv()

MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/sse")
MODEL = os.getenv("LITELLM_MODEL", "claude-sonnet-4-6")

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
        "type": "function",
        "function": {
            "name": "get_system_diagnostics",
            "description": "Get NiFi system health: heap, CPU, JVM version, uptime.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_process_groups",
            "description": "List direct child process groups of group_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "default": "root"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_processors",
            "description": "List all processors in group_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "default": "root"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_flow_status",
            "description": "Get running/stopped/invalid counts for a process group.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "default": "root"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_connections",
            "description": "List all connections with queue depth in group_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "default": "root"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_queue_status",
            "description": "Get current queue depth for a specific connection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "connection_id": {"type": "string"}
                },
                "required": ["connection_id"]
            }
        }
    }
]


async def run_monitor_agent(user_message: str) -> str:
    """Run the monitor agent with a user message."""
    skill_path = os.path.join(os.path.dirname(__file__),
                              "../../skills/nifipilot-agent.md")
    skill_content = ""
    if os.path.exists(skill_path):
        with open(skill_path, "r") as f:
            skill_content = f.read()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"{user_message}\n\n---\nSkill reference:\n{skill_content}"
        }
    ]

    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            while True:
                response = await litellm.acompletion(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                    max_tokens=4096
                )

                choice = response.choices[0]
                messages.append(choice.message.model_dump(exclude_none=True))

                if not choice.message.tool_calls:
                    return choice.message.content or "No response generated."

                tool_results = []
                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_input = json.loads(tool_call.function.arguments)
                    print(f"  🔧 Calling {tool_name}({json.dumps(tool_input)})")
                    result = await session.call_tool(tool_name, tool_input)
                    parts = [
                        item.text if hasattr(item, "text") else str(item)
                        for item in result.content
                    ]
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "\n".join(parts) if parts else "No output"
                    })

                messages.extend(tool_results)


if __name__ == "__main__":
    print("NiFiPilot Monitor Agent")
    print("=" * 40)
    result = asyncio.run(run_monitor_agent(
        "Check the current state of NiFi and report any issues."
    ))
    print(result)
