"""
NiFiPilot Builder Agent
-----------------------
Sub-agent specialized in creating NiFi flows from natural language.

Uses LiteLLM (multi-provider) + NiFiPilot MCP write tools via SSE.
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
You are a NiFi flow architect with access to NiFiPilot MCP tools.
Your role is to CREATE NiFi flows from natural language descriptions.

Follow the NiFiPilot Agent Skill rules for building:
1. Always call get_process_groups first to understand existing structure
2. Create process group FIRST, then processors, then connections
3. Use x coordinates separated by 200px for horizontal flows
4. Use y coordinates separated by 200px for vertical flows
5. ALWAYS confirm with get_processors after creating
6. NEVER start processors — that is the ops agent's job
7. Use dry_run=true if user asks to preview first

Common processor types:
- org.apache.nifi.processors.standard.GetFile
- org.apache.nifi.processors.standard.GenerateFlowFile
- org.apache.nifi.processors.standard.UpdateAttribute
- org.apache.nifi.processors.standard.EvaluateJsonPath
- org.apache.nifi.processors.standard.RouteOnAttribute
- org.apache.nifi.processors.standard.PutFile
- org.apache.nifi.processors.standard.InvokeHTTP
- org.apache.nifi.processors.standard.LogAttribute
- org.apache.nifi.processors.standard.PutDatabaseRecord

Response format:
- Report each action as it completes
- End with a summary table of all created components
- Include IDs for each component
- Suggest next steps (configure, start, etc.)
"""

TOOLS = [
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
            "name": "create_process_group",
            "description": "Create a new process group inside parent_group_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "parent_group_id": {"type": "string", "default": "root"},
                    "x": {"type": "number", "default": 400},
                    "y": {"type": "number", "default": 400}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_processor",
            "description": "Add a new processor to group_id. processor_type is the full Java class name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "processor_type": {"type": "string"},
                    "group_id": {"type": "string", "default": "root"},
                    "x": {"type": "number", "default": 400},
                    "y": {"type": "number", "default": 400}
                },
                "required": ["name", "processor_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_processor",
            "description": "Update a processor's name, config properties, or scheduling period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "processor_id": {"type": "string"},
                    "name": {"type": "string"},
                    "properties": {"type": "object"},
                    "scheduling_period": {"type": "string"}
                },
                "required": ["processor_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_connection",
            "description": "Connect source_id to destination_id within group_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "destination_id": {"type": "string"},
                    "group_id": {"type": "string", "default": "root"},
                    "relationships": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["success"]
                    },
                    "source_type": {"type": "string", "default": "PROCESSOR"},
                    "destination_type": {"type": "string", "default": "PROCESSOR"}
                },
                "required": ["source_id", "destination_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_processor",
            "description": "Delete a stopped processor by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "processor_id": {"type": "string"}
                },
                "required": ["processor_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_process_group",
            "description": "Delete a stopped process group by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_id": {"type": "string"}
                },
                "required": ["group_id"]
            }
        }
    }
]


async def run_builder_agent(user_message: str) -> str:
    """Run the builder agent with a user message."""
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
                    print(f"  🔧 {tool_name}({json.dumps(tool_input)})")
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
    print("NiFiPilot Builder Agent")
    print("=" * 40)
    result = asyncio.run(run_builder_agent(
        "Create a process group called 'API-Ingest' with a "
        "HandleHttpRequest processor connected to a LogAttribute "
        "processor connected to a HandleHttpResponse processor. "
        "Position them vertically starting at y=200."
    ))
    print(result)
