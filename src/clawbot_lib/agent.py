"""AI Agent with RAG, Memory, and MCP integration."""

import json
import re
from typing import Any

from openai import OpenAI

from .channels import slack as slack_actions
from .config import settings
from .database import add_message, get_session_history
from .logger import get_logger
from .mcp import (
    execute_mcp_tool,
    format_mcp_result,
    get_all_mcp_tools,
    mcp_tools_to_openai,
    parse_tool_name,
)
from .mcp import (
    is_mcp_enabled as is_mcp_on,
)
from .memory import (
    add_memory,
    build_memory_context,
    delete_all_memories,
    delete_memory,
    get_all_memories,
    search_memory,
)
from .memory import (
    is_memory_enabled as is_memory_on,
)
from .models import AgentContext, AgentResponse, MessageRole
from .rag import (
    build_context_string as build_rag_context,
)
from .rag import (
    parse_query_filters as parse_rag_filters,
)
from .rag import (
    retrieve,
    should_use_rag,
)
from .tools import scheduler

logger = get_logger("agent")

# Initialize AI client
_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None and settings.ai.openai_api_key:
        _openai_client = OpenAI(api_key=settings.ai.openai_api_key)
    return _openai_client


# System prompt
SYSTEM_PROMPT = """You are a helpful AI assistant integrated into Slack.

## MANDATORY TOOL USAGE - READ CAREFULLY:

You have access to GitHub and Notion via tools. You MUST use them.

### GitHub Rules (ALWAYS FOLLOW):
- User says "repos", "repositories", "GitHub", "issues", "PR", "code" → MUST call a github_* tool
- "List my repos" → call github_search_repositories with query "user:{username}"
- "Create an issue" → call github_create_issue
- NEVER say "I don't have access to GitHub" - YOU DO via tools!
- If you don't know the username, ASK, then use the tool

### Notion Rules (ALWAYS FOLLOW):
- User says "Notion", "pages", "docs", "notes", "workspace" → MUST call a notion_* tool
- "Search Notion" → call notion_search
- NEVER say "I don't have access to Notion" - YOU DO via tools!

### Slack History Rules:
- User asks about past discussions → call search_knowledge_base
- User wants recent messages → call get_channel_history

## CRITICAL INSTRUCTION:
When in doubt, USE THE TOOL. Never refuse by saying you don't have access.
If a tool fails, report the error. But ALWAYS TRY FIRST.

## Available Tool Categories:
- github_* : 26 tools for GitHub (repos, issues, PRs, files, etc.)
- notion_* : 21 tools for Notion (search, pages, databases)
- Slack tools: search_knowledge_base, send_message, get_channel_history, etc.

## Response Format:
- Be concise
- Use Slack formatting: *bold*, _italic_, `code`
- For GitHub/Notion results, format nicely with links"""


# Slack tool definitions
SLACK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "PRIORITY TOOL: Search through indexed Slack message history using semantic search. Use this for ANY question about past discussions, topics, decisions, or finding what was said.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "channel_name": {
                        "type": "string",
                        "description": "Optional: limit to specific channel",
                    },
                    "limit": {"type": "number", "description": "Number of results (default 10)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to a Slack user or channel immediately",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Channel name or user name"},
                    "message": {"type": "string", "description": "The message to send"},
                },
                "required": ["target", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_channel_history",
            "description": "Get LIVE recent messages from a Slack channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_name": {
                        "type": "string",
                        "description": "Channel name without # prefix",
                    },
                    "limit": {"type": "number", "description": "Number of messages (default 20)"},
                },
                "required": ["channel_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_message",
            "description": "Schedule a one-time message to be sent later",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Channel or user name"},
                    "message": {"type": "string", "description": "Message to send"},
                    "send_at": {"type": "string", "description": "ISO 8601 timestamp"},
                },
                "required": ["target", "message", "send_at"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_recurring_message",
            "description": "Schedule a recurring message (daily, weekly, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Channel name"},
                    "message": {"type": "string", "description": "Message to send"},
                    "schedule": {
                        "type": "string",
                        "description": "Schedule like 'every day at 10am'",
                    },
                },
                "required": ["target", "message", "schedule"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder for the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Reminder text"},
                    "time": {"type": "string", "description": "When to remind"},
                },
                "required": ["text", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_channels",
            "description": "List all accessible Slack channels",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": "List all users in the workspace",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_memories",
            "description": "Show what the bot remembers about the user",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_this",
            "description": "Store something the user wants to remember",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact to remember"},
                },
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_about",
            "description": "Delete specific memories",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic to forget"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_everything",
            "description": "Delete ALL memories about the user",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _get_all_tools() -> list[dict[str, Any]]:
    """Get all available tools (Slack + MCP)."""
    all_tools = list(SLACK_TOOLS)

    if is_mcp_on():
        mcp_tools = get_all_mcp_tools()
        openai_mcp_tools = mcp_tools_to_openai(mcp_tools)
        all_tools.extend(openai_mcp_tools)
        logger.info(
            f"Total tools: {len(all_tools)} ({len(SLACK_TOOLS)} Slack + {len(openai_mcp_tools)} MCP)"
        )
    else:
        logger.debug(f"Using {len(SLACK_TOOLS)} Slack tools only")

    return all_tools


async def _execute_tool(
    name: str,
    args: dict[str, Any],
    context: AgentContext,
) -> str:
    """Execute a tool call."""
    logger.info(f"Executing tool: {name}")

    try:
        match name:
            # RAG tool
            case "search_knowledge_base":
                query = args.get("query", "")
                channel_name_filter = args.get("channel_name")
                limit = args.get("limit", 10)

                # Clean query
                query = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"#\1", query).replace("<!>", "").strip()

                # Parse filters
                filters = parse_rag_filters(query)
                if not channel_name_filter:
                    channel_name_filter = filters.get("channel_name")

                logger.info(f"RAG search: query={query}, channel={channel_name_filter}")

                results = await retrieve(
                    query,
                    limit=limit,
                    channel_name=channel_name_filter,
                    min_score=0.3,
                )

                if not results.results:
                    return f'No relevant messages found for "{query}"'

                formatted = "\n".join(
                    f"{i + 1}. {r.formatted} (relevance: {int(r.score * 100)}%)"
                    for i, r in enumerate(results.results)
                )
                return f"Found {len(results.results)} relevant messages:\n\n{formatted}"

            # Messaging tools
            case "send_message":
                success, error = await slack_actions.send_message(
                    args["target"],
                    args["message"],
                )
                return f"{'✅ Message sent' if success else f'❌ Failed: {error}'}"

            case "get_channel_history":
                channel = await slack_actions.find_channel(args["channel_name"])
                if not channel:
                    return f"❌ Channel not found: {args['channel_name']}"

                messages = await slack_actions.get_channel_history(
                    channel.id, args.get("limit", 20)
                )
                if not messages:
                    return f"No messages in #{channel.name}"

                formatted = slack_actions.format_messages_for_context(messages)
                return f"Recent messages from #{channel.name}:\n\n{formatted}"

            # Scheduling tools
            case "schedule_message":
                from datetime import datetime

                send_at = args["send_at"]
                if isinstance(send_at, str):
                    send_at = datetime.fromisoformat(send_at.replace("Z", "+00:00"))

                success, error = await slack_actions.schedule_message(
                    args["target"],
                    args["message"],
                    send_at,
                )
                return f"{'✅ Scheduled' if success else f'❌ Failed: {error}'}"

            case "schedule_recurring_message":
                schedule_str = args["schedule"].lower()
                target_str = args["target"].lstrip("#")

                # Parse schedule
                time_match = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", schedule_str)
                hours, minutes = 9, 0
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2) or 0)
                    period = time_match.group(3)
                    if period == "pm" and hours < 12:
                        hours += 12
                    if period == "am" and hours == 12:
                        hours = 0

                # Determine cron
                if "every day" in schedule_str or "daily" in schedule_str:
                    cron = f"{minutes} {hours} * * *"
                elif "weekday" in schedule_str:
                    cron = f"{minutes} {hours} * * 1-5"
                elif "monday" in schedule_str:
                    cron = f"{minutes} {hours} * * 1"
                else:
                    return f"❌ Could not parse schedule: {args['schedule']}"

                channel = await slack_actions.find_channel(target_str)
                if not channel:
                    return f"❌ Channel not found: {args['target']}"

                task = await scheduler.schedule_task(
                    context.user_id,
                    channel.id,
                    f"📢 {args['message']}",
                    None,
                    cron,
                )

                return f"✅ Recurring message scheduled!\nChannel: #{channel.name}\nSchedule: {args['schedule']}\nTask #{task.id}"

            case "set_reminder":
                success, error = await slack_actions.set_reminder(
                    context.user_id,
                    args["text"],
                    args["time"],
                )
                return f"{'✅ Reminder set' if success else f'❌ Failed: {error}'}"

            # Info tools
            case "list_channels":
                channels = await slack_actions.list_channels()
                member_channels = [c for c in channels if c.is_member]
                return f"Channels ({len(member_channels)}):\n" + "\n".join(
                    f"• #{c.name}" for c in member_channels
                )

            case "list_users":
                users = await slack_actions.list_users()
                user_list = "\n".join(f"• {u.real_name or u.name} (@{u.name})" for u in users[:20])
                return f"Users ({len(users)}):\n{user_list}{'\n...' if len(users) > 20 else ''}"

            # Memory tools
            case "get_my_memories":
                if not is_memory_on():
                    return "❌ Memory feature is not enabled."

                memories = await get_all_memories(context.user_id)
                if not memories:
                    return "I don't have any memories about you yet."

                return "Here's what I remember:\n\n" + "\n".join(
                    f"{i + 1}. {m.memory}" for i, m in enumerate(memories)
                )

            case "remember_this":
                if not is_memory_on():
                    return "❌ Memory feature is not enabled."

                await add_memory(
                    [{"role": "user", "content": f"Please remember: {args['fact']}"}],
                    context.user_id,
                )
                return f"✅ I'll remember: {args['fact']}"

            case "forget_about":
                if not is_memory_on():
                    return "❌ Memory feature is not enabled."

                memories = await search_memory(args["topic"], context.user_id, 5)
                if not memories:
                    return f"No memories about '{args['topic']}'"

                deleted = 0
                for mem in memories:
                    if mem.id and await delete_memory(mem.id):
                        deleted += 1

                return f"✅ Forgot {deleted} memories about '{args['topic']}'"

            case "forget_everything":
                if not is_memory_on():
                    return "❌ Memory feature is not enabled."

                await delete_all_memories(context.user_id)
                return "✅ I've forgotten everything about you."

            # MCP tools
            case _:
                parsed = parse_tool_name(name)
                if parsed:
                    server_name, tool_name = parsed
                    result = await execute_mcp_tool(server_name, tool_name, args)
                    return format_mcp_result(result)

                return f"Unknown tool: {name}"

    except Exception as e:
        logger.error(f"Tool execution failed: {name}", exc_info=True)
        return f"❌ Error: {e}"


async def process_message(
    user_message: str,
    context: AgentContext,
) -> AgentResponse:
    """Process a message with RAG, memory, and MCP.

    This is the main entry point for the agent.

    Args:
        user_message: The user's message
        context: Execution context

    Returns:
        Agent response
    """
    logger.info(f"Processing message for session: {context.session_id}")

    # Save user message
    await add_message(context.session_id, MessageRole.USER, user_message)

    # Get context
    rag_context = ""
    rag_used = False
    sources_count = 0
    memory_context = ""
    memory_used = False
    memories_count = 0

    # 1. Retrieve memories
    if settings.memory.enabled and is_memory_on():
        try:
            memories = await search_memory(user_message, context.user_id, 5)
            if memories:
                memory_context = build_memory_context(memories)
                memory_used = True
                memories_count = len(memories)
        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")

    # 2. Check RAG
    if settings.rag.enabled and should_use_rag(user_message):
        try:
            filters = parse_rag_filters(user_message)
            results = await retrieve(
                user_message,
                limit=settings.rag.max_results,
                min_score=settings.rag.min_similarity,
                channel_name=filters.get("channel_name"),
            )
            if results.results:
                rag_context = build_rag_context(results.results)
                rag_used = True
                sources_count = len(results.results)
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")

    # 3. Build messages for LLM
    history = await get_session_history(context.session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if memory_context:
        messages.append({"role": "system", "content": memory_context})

    if rag_context:
        messages.append({"role": "system", "content": f"Relevant Slack history:\n\n{rag_context}"})

    # Add conversation history
    for msg in history[-10:]:
        messages.append({"role": msg.role.value, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

    # 4. Call LLM
    tools = _get_all_tools()
    logger.info(f"Calling LLM with {len(tools)} tools")

    client = _get_openai_client()
    if not client:
        return AgentResponse(
            content="AI client not configured. Please set OPENAI_API_KEY.",
            should_thread=False,
        )

    model = settings.ai.default_model
    if "gpt" not in model.lower():
        model = "gpt-4o"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            tools=tools,  # type: ignore
            tool_choice="auto",
            max_tokens=4096,
        )

        assistant_message = response.choices[0].message

        # Handle tool calls
        while assistant_message.tool_calls:
            messages.append(assistant_message.model_dump())  # type: ignore

            for tool_call in assistant_message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = await _execute_tool(tool_call.function.name, args, context)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

            response = client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                tools=tools,  # type: ignore
                tool_choice="auto",
                max_tokens=4096,
            )
            assistant_message = response.choices[0].message

        content = assistant_message.content or "I encountered an error."

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        content = f"Error: {e}"

    # Save response
    await add_message(context.session_id, MessageRole.ASSISTANT, content)

    # Store memory (async)
    if settings.memory.enabled and is_memory_on():
        try:
            await add_memory(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": content},
                ],
                context.user_id,
            )
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")

    return AgentResponse(
        content=content,
        should_thread=context.thread_ts is not None or len(content) > 500,
        rag_used=rag_used,
        sources_count=sources_count,
        memory_used=memory_used,
        memories_count=memories_count,
    )


async def summarize_thread(
    messages: list,
    context: AgentContext,
) -> str:
    """Summarize thread messages."""
    if not messages:
        return "No messages to summarize."

    conversation = "\n\n".join(f"[{msg.role.value}]: {msg.content}" for msg in messages)

    prompt = f"""Please summarize this Slack conversation:
1. Key topics discussed
2. Important decisions
3. Action items
4. Unresolved questions

Conversation:
{conversation}

Summary:"""

    client = _get_openai_client()
    if not client:
        return "AI client not configured"

    model = settings.ai.default_model
    if "gpt" not in model.lower():
        model = "gpt-4o"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You summarize conversations concisely."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content or "Failed to generate summary."
    except Exception as e:
        return f"Error: {e}"


# Aliases
processMessage = process_message
summarizeThread = summarize_thread
