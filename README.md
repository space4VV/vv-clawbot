# 🤖 vv-clawbot

> **An intelligent agent powered by RAG (Retrieval Augmented Generation), long-term memory (mem0), and MCP (Model Context Protocol) for GitHub & Notion integration.**

[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![Slack](https://img.shields.io/badge/Slack-Bolt.js-purple.svg)](https://slack.dev/bolt-js/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
  - [High-Level Architecture](#high-level-architecture)
  - [Component Deep Dive](#component-deep-dive)
- [How It Works](#-how-it-works)
  - [Message Processing Flow](#message-processing-flow)
  - [RAG System](#1-rag-retrieval-augmented-generation)
  - [Memory System](#2-memory-system-mem0)
  - [MCP Integration](#3-mcp-model-context-protocol)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [Available Tools](#-available-tools)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

vv-clawbot is a conversational AI agent that combines three powerful systems:

| System | Purpose | Technology |
|--------|---------|------------|
| **RAG** | Search & retrieve historical Slack messages | Vector embeddings + Semantic search |
| **Memory** | Remember user preferences & context across sessions | mem0.ai cloud |
| **MCP** | Interact with external tools (GitHub, Notion) | Model Context Protocol |

### What Makes This Special?

```
Traditional Bot:  User → LLM → Response (no context, no memory, no tools)

This Bot:         User → Memory Recall → RAG Context → LLM + 59 Tools → Action → Memory Storage
                         ↓                ↓                    ↓
                   "User prefers..."  "In Slack on Oct 5..."  "Created GitHub issue #42"
```

---

## ✨ Features

### 🔍 RAG (Retrieval Augmented Generation)
- **Semantic search** across indexed Slack messages
- **Background indexing** of channels (runs every 60 minutes)
- **Smart retrieval** with relevance scoring
- Works even when bot can't access live channel

### 🧠 Long-Term Memory
- **Automatic fact extraction** from conversations
- **Personalized responses** based on user history
- **User-controlled** - view, add, or delete memories
- **Cross-session persistence** - remembers across conversations

### 🔌 MCP (Model Context Protocol)
- **GitHub Integration** (26 tools)
  - Search repositories, create issues, read files
  - List PRs, commits, manage code
- **Notion Integration** (21 tools)
  - Search pages, query databases
  - Read and update content

### 💬 Slack Features
- **DM conversations** with pairing/approval system
- **Channel mentions** with @bot
- **Thread summarization** with `/summarize`
- **Message scheduling** and reminders
- **Typing indicators** and reactions

---

## 🏗 Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SLACK WORKSPACE                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  #general   │  │  #dev-team  │  │    DMs      │  │  @mentions  │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SLACK BOLT.JS (Socket Mode)                            │
│                              Event Handler Layer                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AI AGENT (GPT-4o)                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         CONTEXT ASSEMBLY                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │   │
│  │  │   MEMORY     │  │     RAG      │  │   SESSION    │                   │   │
│  │  │   CONTEXT    │  │   CONTEXT    │  │   HISTORY    │                   │   │
│  │  │              │  │              │  │              │                   │   │
│  │  │ "User is     │  │ "On Oct 5,   │  │ Last 10      │                   │   │
│  │  │  co-founder  │  │  team said   │  │ messages     │                   │   │
│  │  │  of Vizuara" │  │  about..."   │  │ in thread    │                   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                            │
│                                    ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         59 AVAILABLE TOOLS                               │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │   │
│  │  │  SLACK TOOLS   │  │  GITHUB TOOLS  │  │  NOTION TOOLS  │             │   │
│  │  │   (12 tools)   │  │   (26 tools)   │  │   (21 tools)   │             │   │
│  │  │                │  │                │  │                │             │   │
│  │  │ • search_kb    │  │ • create_issue │  │ • search       │             │   │
│  │  │ • send_message │  │ • list_repos   │  │ • get_page     │             │   │
│  │  │ • get_history  │  │ • get_file     │  │ • query_db     │             │   │
│  │  │ • schedule     │  │ • list_PRs     │  │ • create_page  │             │   │
│  │  │ • remind       │  │ • search_code  │  │ • update       │             │   │
│  │  │ • memory ops   │  │ • ...          │  │ • ...          │             │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   VECTOR STORE   │    │   MEM0 CLOUD     │    │   MCP SERVERS    │
│   (ChromaDB)     │    │                  │    │                  │
│                  │    │                  │    │  ┌────────────┐  │
│  254 indexed     │    │  User memories   │    │  │   GitHub   │  │
│  Slack messages  │    │  & preferences   │    │  │   Server   │  │
│                  │    │                  │    │  └────────────┘  │
│  Embeddings:     │    │  Extraction:     │    │  ┌────────────┐  │
│  OpenAI          │    │  gpt-4o-mini     │    │  │   Notion   │  │
│  text-embed-3    │    │                  │    │  │   Server   │  │
│                  │    │                  │    │  └────────────┘  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
          │                         │                         │
          │                         │                         │
          ▼                         ▼                         ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   LOCAL DISK     │    │   MEM0 API       │    │  EXTERNAL APIs   │
│   ./data/        │    │   (Cloud)        │    │  GitHub, Notion  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

---

### Component Deep Dive

#### 1. Slack Layer (`src/channels/slack.ts`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SLACK EVENT HANDLER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INCOMING EVENTS:                                               │
│  ├── message (DM)        → Check approval → Process             │
│  ├── message (channel)   → Check @mention → Process             │
│  ├── app_mention         → Process directly                     │
│  ├── reaction_added      → Log/handle                           │
│  └── slash_commands      → /approve, /status                    │
│                                                                 │
│  SPECIAL HANDLERS:                                              │
│  ├── "help"              → Show help message                    │
│  ├── "summarize"/"tldr"  → Summarize thread                     │
│  ├── "my tasks"          → List scheduled tasks                 │
│  ├── "cancel task N"     → Cancel task                          │
│  └── "/reset"            → Clear conversation                   │
│                                                                 │
│  REGULAR FLOW:                                                  │
│  └── All other messages  → processMessage() in agent.ts        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2. Agent Layer (`src/agents/agent.ts`)

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI AGENT                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  processMessage(userMessage, context)                           │
│  │                                                              │
│  ├── 1. MEMORY RETRIEVAL                                        │
│  │   └── searchMemory(message, userId) → memoryContext          │
│  │                                                              │
│  ├── 2. RAG PRE-CHECK                                           │
│  │   └── shouldUseRAG(message) ? retrieve() → ragContext        │
│  │                                                              │
│  ├── 3. BUILD MESSAGES                                          │
│  │   ├── System prompt (with tool instructions)                 │
│  │   ├── Memory context (if found)                              │
│  │   ├── RAG context (if found)                                 │
│  │   ├── Session history (last 10 messages)                     │
│  │   └── Current user message                                   │
│  │                                                              │
│  ├── 4. GET ALL TOOLS                                           │
│  │   ├── SLACK_TOOLS (12 built-in)                              │
│  │   └── MCP_TOOLS (47 from GitHub + Notion)                    │
│  │                                                              │
│  ├── 5. LLM CALL (GPT-4o)                                       │
│  │   └── Loop while tool_calls exist:                           │
│  │       ├── Execute tool (Slack or MCP)                        │
│  │       ├── Add result to messages                             │
│  │       └── Call LLM again                                     │
│  │                                                              │
│  ├── 6. MEMORY STORAGE (async, background)                      │
│  │   └── addMemory(conversation) → extract & store facts        │
│  │                                                              │
│  └── 7. RETURN RESPONSE                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3. Tool Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   TOOL EXECUTION                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  executeTool(name, args, context)                               │
│  │                                                              │
│  ├── SLACK TOOLS (handled directly):                            │
│  │   ├── search_knowledge_base → RAG retrieve()                 │
│  │   ├── send_message → Slack API                               │
│  │   ├── get_channel_history → Slack API                        │
│  │   ├── schedule_message → Slack API                           │
│  │   ├── set_reminder → Slack API                               │
│  │   ├── list_channels → Slack API                              │
│  │   ├── list_users → Slack API                                 │
│  │   ├── get_my_memories → mem0 getAllMemories()                │
│  │   ├── remember_this → mem0 addMemory()                       │
│  │   ├── forget_about → mem0 deleteMemory()                     │
│  │   └── forget_everything → mem0 deleteAllMemories()           │
│  │                                                              │
│  └── MCP TOOLS (routed to MCP servers):                         │
│      │                                                          │
│      ├── parseToolName("github_create_issue")                   │
│      │   └── { serverName: "github", toolName: "create_issue" } │
│      │                                                          │
│      └── executeMCPTool(serverName, toolName, args)             │
│          └── Send JSON-RPC to MCP server process                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 How It Works

### Message Processing Flow

When a user sends a message, here's the complete flow:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ USER: "Search Slack for bugs we discussed, then create GitHub issues for them" │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: SLACK EVENT RECEIVED                                                    │
│ ────────────────────────────                                                    │
│ • Slack Bolt.js receives message event                                          │
│ • Validates: Is this a DM? Is user approved? Is bot mentioned?                  │
│ • Adds 👀 reaction to show processing                                           │
│ • Creates/retrieves session for conversation continuity                         │
│                                                                                 │
│ Log: "Message received from U050Y4SNQF3 in D0AB0RYJTRR"                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: MEMORY RETRIEVAL                                                        │
│ ────────────────────────                                                        │
│ • Query mem0 for relevant memories about this user                              │
│ • Semantic search: "What do I know that's relevant to this message?"            │
│ • Returns: User preferences, past context, stored facts                         │
│                                                                                 │
│ Example memories found:                                                         │
│ • "User's GitHub username is VizuaraAI"                                         │
│ • "User prefers detailed technical explanations"                                │
│ • "User is co-founder of Vizuara AI Labs"                                       │
│                                                                                 │
│ Log: "Retrieved 3 relevant memories"                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: RAG PRE-CHECK                                                           │
│ ─────────────────────                                                           │
│ • Analyze message: Does it ask about past discussions?                          │
│ • Keywords: "discussed", "talked about", "mentioned", "said", etc.              │
│ • If yes: Query vector store for relevant Slack messages                        │
│                                                                                 │
│ • Query: "bugs we discussed"                                                    │
│ • Vector search across 254 indexed messages                                     │
│ • Returns top matches with relevance scores                                     │
│                                                                                 │
│ Log: "RAG triggered for query"                                                  │
│ Log: "Retrieved 5 documents in 384ms"                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: BUILD LLM CONTEXT                                                       │
│ ─────────────────────────                                                       │
│                                                                                 │
│ Messages array sent to GPT-4o:                                                  │
│                                                                                 │
│ [                                                                               │
│   {                                                                             │
│     role: "system",                                                             │
│     content: "You are a helpful AI assistant...                                 │
│               ## MANDATORY TOOL USAGE...                                        │
│               You have access to GitHub and Notion via tools..."                │
│   },                                                                            │
│   {                                                                             │
│     role: "system",                                                             │
│     content: "## What I Remember About You\n                                    │
│               1. User's GitHub username is VizuaraAI\n                          │
│               2. User prefers detailed explanations..."                         │
│   },                                                                            │
│   {                                                                             │
│     role: "system",                                                             │
│     content: "## Relevant Slack History\n                                       │
│               [Oct 5] @john: Found a bug in the login flow...\n                 │
│               [Oct 7] @jane: The API timeout issue is critical..."              │
│   },                                                                            │
│   { role: "user", content: "What's the weather?" },      // Previous           │
│   { role: "assistant", content: "I can't check..." },    // conversation       │
│   { role: "user", content: "Search Slack for bugs..." }  // Current message    │
│ ]                                                                               │
│                                                                                 │
│ + 59 tool definitions attached                                                  │
│                                                                                 │
│ Log: "Total tools available: 59 (12 Slack + 47 MCP)"                            │
│ Log: "Calling LLM with 59 tools"                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: LLM DECISION & TOOL CALLS                                               │
│ ─────────────────────────────────                                               │
│                                                                                 │
│ GPT-4o analyzes the request and decides to call tools:                          │
│                                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ LLM Response #1:                                                            │ │
│ │ {                                                                           │ │
│ │   tool_calls: [                                                             │ │
│ │     {                                                                       │ │
│ │       function: "search_knowledge_base",                                    │ │
│ │       arguments: { query: "bugs", limit: 10 }                               │ │
│ │     }                                                                       │ │
│ │   ]                                                                         │ │
│ │ }                                                                           │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                        │
│                                        ▼                                        │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ TOOL EXECUTION: search_knowledge_base                                       │ │
│ │ • RAG query: "bugs"                                                         │ │
│ │ • Returns: 10 relevant messages about bugs                                  │ │
│ │                                                                             │ │
│ │ Log: "Executing tool: search_knowledge_base"                                │ │
│ │ Log: "RAG search returned 10 results"                                       │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                        │
│                                        ▼                                        │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ LLM Response #2 (with tool results):                                        │ │
│ │ {                                                                           │ │
│ │   tool_calls: [                                                             │ │
│ │     {                                                                       │ │
│ │       function: "github_create_issue",                                      │ │
│ │       arguments: {                                                          │ │
│ │         owner: "VizuaraAI",                                                 │ │
│ │         repo: "nano-kimi",                                                  │ │
│ │         title: "Fix login timeout bug",                                     │ │
│ │         body: "As discussed on Oct 5..."                                    │ │
│ │       }                                                                     │ │
│ │     },                                                                      │ │
│ │     {                                                                       │ │
│ │       function: "github_create_issue",                                      │ │
│ │       arguments: { ... another issue ... }                                  │ │
│ │     }                                                                       │ │
│ │   ]                                                                         │ │
│ │ }                                                                           │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                        │
│                                        ▼                                        │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ TOOL EXECUTION: github_create_issue (via MCP)                               │ │
│ │ • Route to MCP client                                                       │ │
│ │ • MCP client sends JSON-RPC to GitHub server                                │ │
│ │ • GitHub server calls GitHub API                                            │ │
│ │ • Returns: { issue_number: 42, url: "..." }                                 │ │
│ │                                                                             │ │
│ │ Log: "Executing MCP tool: github/create_issue"                              │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                        │
│                                        ▼                                        │
│ ┌─────────────────────────────────────────────────────────────────────────────┐ │
│ │ LLM Response #3 (final):                                                    │ │
│ │ {                                                                           │ │
│ │   content: "I searched Slack and found 10 discussions about bugs.           │ │
│ │             I've created 2 GitHub issues:\n                                 │ │
│ │             • #42: Fix login timeout bug\n                                  │ │
│ │             • #43: API response caching issue"                              │ │
│ │ }                                                                           │ │
│ └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: MEMORY STORAGE (Background)                                             │
│ ───────────────────────────────────                                             │
│                                                                                 │
│ • After response is sent, analyze conversation for facts                        │
│ • mem0 extracts: "User asked about bugs in Slack discussions"                   │
│ • Stores for future context                                                     │
│                                                                                 │
│ Log: "Stored 1 memories for user U050Y4SNQF3"                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 7: SEND RESPONSE                                                           │
│ ─────────────────────                                                           │
│                                                                                 │
│ • Remove 👀 reaction                                                            │
│ • Send formatted response to Slack                                              │
│ • Thread if needed (long response or existing thread)                           │
│                                                                                 │
│ Final message to user:                                                          │
│ "I searched Slack and found 10 discussions about bugs.                          │
│  I've created 2 GitHub issues:                                                  │
│  • #42: Fix login timeout bug                                                   │
│  • #43: API response caching issue"                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### 1. RAG (Retrieval Augmented Generation)

#### What is RAG?

RAG allows the bot to search through historical Slack messages and use them as context for responses. Instead of the LLM making up information, it retrieves real data from your workspace.

#### How RAG Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAG PIPELINE                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

                            INDEXING PHASE (Background)
                            ═══════════════════════════

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    SLACK     │     │   MESSAGE    │     │  EMBEDDING   │     │   VECTOR     │
│   CHANNELS   │────▶│  EXTRACTOR   │────▶│   MODEL      │────▶│    STORE     │
│              │     │              │     │              │     │              │
│ #general     │     │ • Text       │     │ OpenAI       │     │ ChromaDB     │
│ #dev-team    │     │ • User       │     │ text-embed-  │     │ (Local)      │
│ #random      │     │ • Timestamp  │     │ 3-small      │     │              │
│              │     │ • Channel    │     │              │     │ 254 docs     │
│              │     │ • Thread     │     │ 1536 dims    │     │ indexed      │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

                            RETRIEVAL PHASE (Query Time)
                            ════════════════════════════

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    USER      │     │  EMBEDDING   │     │   VECTOR     │     │   RANKED     │
│    QUERY     │────▶│   MODEL      │────▶│   SEARCH     │────▶│   RESULTS    │
│              │     │              │     │              │     │              │
│ "What bugs   │     │ Same model   │     │ Cosine       │     │ Top 10 most  │
│  did we      │     │ as indexing  │     │ similarity   │     │ relevant     │
│  discuss?"   │     │              │     │              │     │ messages     │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

#### RAG Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `RAG_ENABLED` | `true` | Enable/disable RAG |
| `RAG_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `RAG_MAX_RESULTS` | `10` | Max documents to retrieve |
| `RAG_MIN_SIMILARITY` | `0.3` | Minimum relevance score (0-1) |
| `RAG_INDEX_INTERVAL_MINUTES` | `60` | How often to re-index |

#### Key Files

- `src/rag/vectorstore.ts` - Vector storage (ChromaDB)
- `src/rag/embeddings.ts` - OpenAI embeddings
- `src/rag/indexer.ts` - Background message indexer
- `src/rag/retriever.ts` - Semantic search

---

### 2. Memory System (mem0)

#### What is mem0?

mem0 is a cloud-based memory system that automatically extracts and stores facts from conversations. It enables the bot to remember user preferences, context, and history across sessions.

#### How Memory Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            MEMORY PIPELINE                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

                            STORAGE PHASE (After Response)
                            ══════════════════════════════

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ CONVERSATION │     │    GPT-4o    │     │    FACT      │     │   MEM0       │
│              │────▶│    MINI      │────▶│  EXTRACTION  │────▶│   CLOUD      │
│              │     │              │     │              │     │              │
│ User: "My    │     │ Analyzes     │     │ Extracted:   │     │ Stores per   │
│  GitHub is   │     │ conversation │     │ "User's      │     │ user_id      │
│  VizuaraAI"  │     │ for facts    │     │  GitHub is   │     │              │
│              │     │              │     │  VizuaraAI"  │     │ Searchable   │
│ Bot: "Got    │     │              │     │              │     │ via API      │
│  it!"        │     │              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘

                            RETRIEVAL PHASE (Before LLM Call)
                            ═════════════════════════════════

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    USER      │     │   MEM0       │     │  SEMANTIC    │     │  MEMORY      │
│   MESSAGE    │────▶│   CLOUD      │────▶│   SEARCH     │────▶│  CONTEXT     │
│              │     │              │     │              │     │              │
│ "List my     │     │ Query by     │     │ Find         │     │ "User's      │
│  repos"      │     │ user_id +    │     │ relevant     │     │  GitHub is   │
│              │     │ semantic     │     │ memories     │     │  VizuaraAI"  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
                                                              Added to LLM context
```

#### Memory Types

| Type | Example | How It's Used |
|------|---------|---------------|
| **Preferences** | "User prefers concise responses" | Adjusts response style |
| **Identity** | "User is co-founder of Vizuara" | Personalizes context |
| **Technical** | "User's GitHub is VizuaraAI" | Pre-fills tool arguments |
| **Projects** | "User is working on nano-kimi" | Understands context |
| **Interests** | "User cares about SOP, LOR" | Prioritizes topics |

#### Memory Tools (User-Controlled)

```
"What do you remember about me?"     → get_my_memories
"Remember that I prefer Python"      → remember_this
"Forget about my old project"        → forget_about
"Forget everything about me"         → forget_everything
```

---

### 3. MCP (Model Context Protocol)

#### What is MCP?

MCP is Anthropic's open standard for connecting AI models to external tools. Instead of hardcoding integrations, MCP provides a standardized protocol for tool discovery and execution.

#### How MCP Works

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MCP ARCHITECTURE                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SLACK BOT PROCESS                                   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           MCP CLIENT                                     │   │
│  │                        (src/mcp/client.ts)                               │   │
│  │                                                                          │   │
│  │   • Spawns MCP server processes                                          │   │
│  │   • Discovers available tools                                            │   │
│  │   • Routes tool calls via JSON-RPC                                       │   │
│  │   • Handles responses                                                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                            │
│                    ┌───────────────┴───────────────┐                           │
│                    │           stdio               │                            │
│                    │      (stdin/stdout)           │                            │
│                    ▼                               ▼                            │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐           │
│  │      GITHUB MCP SERVER       │  │      NOTION MCP SERVER       │           │
│  │                              │  │                              │           │
│  │  npx @modelcontextprotocol/  │  │  npx @notionhq/              │           │
│  │      server-github           │  │      notion-mcp-server       │           │
│  │                              │  │                              │           │
│  │  26 tools available:         │  │  21 tools available:         │           │
│  │  • search_repositories       │  │  • search                    │           │
│  │  • create_issue              │  │  • get_page                  │           │
│  │  • get_file_contents         │  │  • query_database            │           │
│  │  • list_pull_requests        │  │  • create_page               │           │
│  │  • ...                       │  │  • ...                       │           │
│  └──────────────────────────────┘  └──────────────────────────────┘           │
│                    │                               │                            │
└────────────────────┼───────────────────────────────┼────────────────────────────┘
                     │                               │
                     ▼                               ▼
           ┌──────────────────┐            ┌──────────────────┐
           │   GITHUB API     │            │   NOTION API     │
           │                  │            │                  │
           │  api.github.com  │            │  api.notion.com  │
           └──────────────────┘            └──────────────────┘
```

#### MCP Initialization Flow

```
STARTUP:
────────
1. Load config (env vars or mcp-config.json)
2. For each server:
   a. Spawn process: npx @modelcontextprotocol/server-xxx
   b. Send: initialize request
   c. Send: notifications/initialized
   d. Send: tools/list
   e. Store discovered tools

TOOL CALL:
──────────
1. LLM returns: { tool: "github_create_issue", args: {...} }
2. Parse: serverName="github", toolName="create_issue"
3. Find server process
4. Send JSON-RPC: { method: "tools/call", params: { name, arguments } }
5. Wait for response
6. Return result to LLM
```

#### JSON-RPC Communication

```json
// Request (Bot → MCP Server)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_issue",
    "arguments": {
      "owner": "VizuaraAI",
      "repo": "nano-kimi",
      "title": "Fix bug",
      "body": "Description..."
    }
  }
}

// Response (MCP Server → Bot)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Created issue #42: https://github.com/..."
      }
    ]
  }
}
```

---

## 📦 Installation

### Prerequisites

- Node.js 18+
- npm or yarn
- Slack workspace (admin access)
- OpenAI API key
- GitHub Personal Access Token (for MCP)
- Notion Integration Token (for MCP)
- mem0 API key (for memory)

### Step 1: Clone & Install

```bash
git clone https://github.com/yourusername/slack-ai-assistant-v2.git
cd slack-ai-assistant-v2
npm install
```

### Step 2: Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Enable **Socket Mode** (Settings → Socket Mode)
4. Add **Bot Token Scopes**:
   - `app_mentions:read`
   - `channels:history`
   - `channels:read`
   - `chat:write`
   - `im:history`
   - `im:read`
   - `im:write`
   - `reactions:read`
   - `reactions:write`
   - `reminders:read`
   - `reminders:write`
   - `users:read`
5. Add **User Token Scopes** (for reminders):
   - `reminders:read`
   - `reminders:write`
6. Install to workspace
7. Copy tokens:
   - Bot Token: `xoxb-...`
   - App Token: `xapp-...`
   - User Token: `xoxp-...`

### Step 3: Get API Keys

**OpenAI:**
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create API key

**GitHub:**
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate new token (classic)
3. Select scopes: `repo`, `issues`

**Notion:**
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create new integration
3. Copy Internal Integration Token
4. Share pages with the integration

**mem0:**
1. Go to [app.mem0.ai](https://app.mem0.ai)
2. Create account and get API key

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_USER_TOKEN=xoxp-your-user-token

# AI
OPENAI_API_KEY=sk-your-openai-key
DEFAULT_MODEL=gpt-4o

# Memory
MEM0_API_KEY=m0-your-mem0-key
MEMORY_ENABLED=true

# MCP
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_github_token
NOTION_API_TOKEN=secret_your_notion_token

# RAG
RAG_ENABLED=true
```

### Step 5: Run

```bash
# Development (with hot reload)
npm run dev

# Production
npm run build
npm start
```

### Expected Output

```
✅ Database initialized
✅ Vector store initialized (254 documents)
✅ Background indexer started
✅ Memory system initialized
✅ MCP initialized: github, notion
✅ Task scheduler started
✅ Slack app started

Features enabled:
  • RAG (Semantic Search): ✅
  • Long-Term Memory: ✅
  • MCP (GitHub/Notion): ✅ github, notion
  • Task Scheduler: ✅
  • AI Model: gpt-4o

Press Ctrl+C to stop
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | ✅ | - | Bot OAuth token (xoxb-) |
| `SLACK_APP_TOKEN` | ✅ | - | App-level token (xapp-) |
| `SLACK_USER_TOKEN` | ❌ | - | User token for reminders |
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key |
| `DEFAULT_MODEL` | ❌ | `gpt-4o` | AI model to use |
| `MEM0_API_KEY` | ❌ | - | mem0 cloud API key |
| `MEMORY_ENABLED` | ❌ | `true` | Enable memory system |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | ❌ | - | GitHub token for MCP |
| `NOTION_API_TOKEN` | ❌ | - | Notion token for MCP |
| `RAG_ENABLED` | ❌ | `true` | Enable RAG |
| `RAG_INDEX_INTERVAL_MINUTES` | ❌ | `60` | Index frequency |
| `LOG_LEVEL` | ❌ | `info` | Log verbosity |

### MCP Configuration (Optional)

Create `mcp-config.json` for custom MCP settings:

```json
{
  "servers": [
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_PERSONAL_ACCESS_TOKEN"
      }
    },
    {
      "name": "notion",
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer $NOTION_API_TOKEN\", \"Notion-Version\": \"2022-06-28\"}"
      }
    }
  ]
}
```

---

## 💡 Usage Examples

### Basic Conversations

```
User: Hello!
Bot:  Hi! How can I help you today?

User: What can you do?
Bot:  I can help with:
      • Searching Slack history for past discussions
      • Managing GitHub repos, issues, and PRs
      • Searching and reading Notion pages
      • Scheduling messages and reminders
      • Remembering your preferences
```

### RAG (Slack Search)

```
User: What did we discuss about the API last week?
Bot:  Based on Slack history, here's what was discussed:

      [Oct 15] @john: "The API timeout is set to 30s, should increase"
      [Oct 16] @jane: "Agreed, let's make it configurable"
      [Oct 17] @john: "Done, deployed to staging"

      Summary: The team discussed API timeout issues and made it configurable.
```

### Memory

```
User: Remember that I prefer Python over JavaScript
Bot:  ✅ Got it! I'll remember that you prefer Python over JavaScript.

------- Later session -------

User: Write a hello world script
Bot:  Here's a Python hello world (since you prefer Python):
      
      print("Hello, World!")
```

### MCP (GitHub)

```
User: List my GitHub repos
Bot:  Here are your repositories:
      1. nano-kimi - Learn to build nano-kimi from scratch
      2. Mixture_of_Experts - MoE implementation
      3. Machine-Learning-Teach-by-Doing
      ...

User: Create an issue for the login bug
Bot:  ✅ Created issue #42 in VizuaraAI/nano-kimi:
      "Login timeout bug"
      https://github.com/VizuaraAI/nano-kimi/issues/42
```

### MCP (Notion)

```
User: Search Notion for project roadmap
Bot:  Found 3 pages matching "project roadmap":
      1. Q4 Product Roadmap (last edited 2 days ago)
      2. Engineering Roadmap 2024
      3. Roadmap Template

      Would you like me to get the content of any of these?
```

### Combined (RAG + Memory + MCP)

```
User: Remember my GitHub is VizuaraAI. Search Slack for bugs we 
      discussed, then create issues for them.

Bot:  ✅ I'll remember your GitHub username.
      
      Searching Slack for bug discussions...
      Found 10 relevant messages.
      
      Creating GitHub issues:
      • #42: Login timeout bug (from Oct 5 discussion)
      • #43: API caching issue (from Oct 12 discussion)
      
      Created 2 issues in VizuaraAI/nano-kimi!
```

---

## 🔧 Available Tools

### Slack Tools (12)

| Tool | Description |
|------|-------------|
| `search_knowledge_base` | Semantic search across indexed Slack messages |
| `send_message` | Send message to channel or user |
| `get_channel_history` | Get recent messages from a channel |
| `schedule_message` | Schedule one-time message |
| `schedule_recurring_message` | Schedule recurring message |
| `set_reminder` | Set a reminder |
| `list_channels` | List all channels |
| `list_users` | List all users |
| `get_my_memories` | Show stored memories |
| `remember_this` | Explicitly store a fact |
| `forget_about` | Delete specific memories |
| `forget_everything` | Delete all memories |

### GitHub Tools via MCP (26)

| Tool | Description |
|------|-------------|
| `github_search_repositories` | Search for repos |
| `github_get_repository` | Get repo details |
| `github_list_issues` | List issues |
| `github_create_issue` | Create new issue |
| `github_get_issue` | Get issue details |
| `github_update_issue` | Update issue |
| `github_list_pull_requests` | List PRs |
| `github_create_pull_request` | Create PR |
| `github_get_file_contents` | Read file from repo |
| `github_search_code` | Search code |
| ... and 16 more |

### Notion Tools via MCP (21)

| Tool | Description |
|------|-------------|
| `notion_search` | Search all pages |
| `notion_get_page` | Get page content |
| `notion_create_page` | Create new page |
| `notion_update_page` | Update page |
| `notion_query_database` | Query database |
| `notion_create_database` | Create database |
| ... and 15 more |

---

## 📁 Project Structure

```
slack-ai-assistant-v2/
├── src/
│   ├── index.ts                 # Main entry point
│   ├── config/
│   │   └── index.ts             # Configuration loading
│   ├── channels/
│   │   └── slack.ts             # Slack event handlers
│   ├── agents/
│   │   └── agent.ts             # AI agent + tool orchestration
│   ├── memory/
│   │   └── database.ts          # SQLite for sessions
│   ├── memory-ai/
│   │   ├── index.ts             # Memory exports
│   │   └── mem0-client.ts       # mem0 integration
│   ├── rag/
│   │   ├── index.ts             # RAG exports
│   │   ├── vectorstore.ts       # ChromaDB storage
│   │   ├── embeddings.ts        # OpenAI embeddings
│   │   ├── indexer.ts           # Background indexer
│   │   └── retriever.ts         # Semantic search
│   ├── mcp/
│   │   ├── index.ts             # MCP exports
│   │   ├── client.ts            # MCP client manager
│   │   ├── config.ts            # MCP configuration
│   │   └── tool-converter.ts    # MCP → OpenAI tool format
│   ├── tools/
│   │   ├── slack-actions.ts     # Slack API wrappers
│   │   └── scheduler.ts         # Task scheduler
│   └── utils/
│       └── logger.ts            # Winston logger
├── data/                        # Local data (gitignored)
│   └── vectorstore/             # ChromaDB files
├── docs/
│   ├── ARCHITECTURE.md          # Architecture details
│   ├── RAG.md                   # RAG documentation
│   ├── MEMORY.md                # Memory documentation
│   └── MCP.md                   # MCP documentation
├── scripts/
│   ├── setup-db.ts              # Database setup
│   └── run-indexer.ts           # Manual indexing
├── .env.example                 # Environment template
├── mcp-config.example.json      # MCP config template
├── package.json
├── tsconfig.json
└── README.md
```

---

## 🐛 Troubleshooting

### Common Issues

#### "MCP server not connected"

```bash
# Check if tokens are set
echo $GITHUB_PERSONAL_ACCESS_TOKEN
echo $NOTION_API_TOKEN

# Test GitHub token
curl -H "Authorization: token $GITHUB_PERSONAL_ACCESS_TOKEN" https://api.github.com/user
```

#### "RAG returns 0 results"

```bash
# Check indexed document count in logs
# Should see: "Vector store initialized (254 documents)"

# Invite bot to more channels
/invite @YourBotName

# Restart to re-index
npm run dev
```

#### "Memory not working"

```
# Check for this warning in logs:
"Failed to initialize client: ReferenceError: window is not defined"

# This is a known mem0 package issue - memory still works via API
```

#### "Bot not responding in channels"

1. Ensure bot is mentioned: `@BotName your message`
2. Check bot is invited to the channel
3. Check `ALLOWED_CHANNELS` in config

#### "Tool not being used"

The LLM decides when to use tools. Be explicit:
```
❌ "What repos do I have?"
✅ "Use GitHub to list my repositories"
✅ "Search my GitHub repos for VizuaraAI"
```

### Debug Mode

Enable verbose logging:
```env
LOG_LEVEL=debug
```

### Logs to Check

```
# Startup
✅ MCP initialized: github, notion     # MCP working
✅ Vector store initialized (254 docs) # RAG working
✅ Memory system initialized           # Memory working

# Message processing
Total tools available: 59 (12 Slack + 47 MCP)  # All tools loaded
Executing tool: github_create_issue            # Tool being called
Executing MCP tool: github/create_issue        # MCP routing
Stored 1 memories for user U050Y4SNQF3         # Memory saving
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Slack Bolt.js](https://slack.dev/bolt-js/) - Slack app framework
- [OpenAI](https://openai.com/) - LLM and embeddings
- [mem0](https://mem0.ai/) - Long-term memory
- [Model Context Protocol](https://modelcontextprotocol.io/) - Tool integration standard
- [ChromaDB](https://www.trychroma.com/) - Vector database

---

<p align="center">
  Built with ❤️ for productive Slack workspaces
</p>
