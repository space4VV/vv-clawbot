# vv-clawbot

An intelligent Slack bot powered by **RAG** (Retrieval Augmented Generation), **mem0** long-term memory, and optional **MCP** (Model Context Protocol) for external tools.

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Slack](https://img.shields.io/badge/Slack-Socket%20Mode-purple.svg)](https://api.slack.com/apis/connections/socket)

---

## Overview

| System | Purpose |
|--------|---------|
| **RAG** | Semantic search over indexed Slack messages (ChromaDB, OpenAI embeddings) |
| **Memory** | User preferences and context across sessions (mem0) |
| **MCP** | Optional external tools (e.g. GitHub, Notion) via Model Context Protocol |

Flow: **User message** → Memory recall + RAG context → **LLM (OpenAI)** + tools → Response → Memory storage.

---

## Features

- **Slack**: Channel @mentions and DMs via Socket Mode; session history in SQLite
- **RAG**: Background indexing of channels, semantic search with configurable similarity
- **Memory**: Optional mem0 integration for cross-session context (requires mem0 API key)
- **MCP**: Optional; connect MCP servers for GitHub, Notion, etc.
- **Scheduler**: Task scheduling (APScheduler)

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (or pip/poetry)
- Slack app with **Socket Mode**, **Bot Token**, and **App-Level Token**
- OpenAI API key (for chat and RAG embeddings)

---

## Installation

```bash
git clone <repo-url>
cd vv-clawbot
uv sync
```

Copy env and set your keys:

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot OAuth token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Yes | App-level token for Socket Mode (`xapp-...`) |
| `AI_OPENAI_API_KEY` or `OPENAI_API_KEY` | Yes | OpenAI API key |
| `SLACK_USER_TOKEN` | No | For reminders (`xoxp-...`) |
| `MEM0_API_KEY` | No | mem0 cloud (enables memory) |
| `RAG_ENABLED` | No | Default `true` |
| `MEMORY_ENABLED` | No | Default `true` |

**Slack app setup**

1. [api.slack.com/apps](https://api.slack.com/apps) → Create/select app → enable **Socket Mode**.
2. **Bot Token Scopes**: `app_mentions:read`, `channels:history`, `channels:read`, `chat:write`, `im:history`, `im:read`, `im:write`, etc.
3. **Subscribe to bot events**: `app_mention` (channel @mentions), `message.im` (DMs).
4. Install to workspace and copy Bot Token and App-Level Token into `.env`.

---

## Run

```bash
uv run vv-clawbot
```

Leave the process running; use Ctrl+C to stop. In Slack, mention the bot in a channel (e.g. `@YourBotName hello`) or DM it.

---

## Project structure

```
vv-clawbot/
├── src/clawbot_lib/
│   ├── main.py          # Entry point, startup/shutdown
│   ├── agent.py         # LLM + tools, message handling
│   ├── config.py        # Pydantic settings (.env)
│   ├── database.py      # SQLite sessions + message history
│   ├── logger.py        # Logging
│   ├── channels/        # Slack (Socket Mode)
│   ├── rag/             # ChromaDB, indexer, retriever
│   ├── memory/         # mem0 integration
│   ├── mcp/             # MCP client (optional servers)
│   ├── models/          # Pydantic models
│   └── tools/           # Scheduler, etc.
├── tests/
├── pyproject.toml
└── .env
```

---

## Configuration (selection)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | `claude-sonnet-4-20250514` | Model name (OpenAI fallback used for chat) |
| `RAG_EMBEDDING_MODEL` | `text-embedding-3-small` | Embeddings model |
| `RAG_VECTOR_DB_PATH` | `./data/chroma` | ChromaDB path |
| `RAG_INDEX_INTERVAL_HOURS` | `1` | Indexing interval |
| `DATABASE_PATH` | `./data/assistant.db` | SQLite DB |
| `LOG_LEVEL` | `info` | Logging level |

---

## Troubleshooting

- **Bot doesn’t reply in channels**  
  Subscribe to **app_mention** under “Subscribe to bot events” and invite the bot to the channel.

- **“AI client not configured”**  
  Set `AI_OPENAI_API_KEY` or `OPENAI_API_KEY` in `.env`. Ensure `.env` is loaded (config loads it at import).

- **Process exits right after start**  
  The app now waits on a shutdown event; it should keep running until Ctrl+C. Restart with `uv run vv-clawbot`.

- **Memory / MCP disabled**  
  Optional. For memory, set `MEM0_API_KEY`. For MCP, configure and run MCP servers as required by `clawbot_lib.mcp`.

---

## Development

```bash
uv sync --extra dev
ruff check src tests
mypy src
pytest
```

---

## License

MIT.
