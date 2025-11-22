# CLAUDE.md

**AFTER EVERY FEATURE IMPLEMENTATION OR CODE MODIFICATION, or major architectural decision that is confirmed to be pushed/merged ALWAYS no matter what, ASK if:**
**"Should I use @agent-claude-md-maintainer to update CLAUDE.md to reflect these changes?"**

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python + Poetry)
```bash
cd backend

# FastAPI Server (the ONLY backend needed for the application)
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# API Documentation
# http://localhost:8000/docs      # Swagger UI
# http://localhost:8000/redoc     # ReDoc
# http://localhost:8000/health    # Health check

# LangGraph dev server (OPTIONAL - only for debugging graphs in isolation)
poetry run langgraph dev                 # Port 2024 (requires langgraph-cli)
# Access LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

# Testing
poetry run pytest                        # All tests
poetry run pytest -m "not integration"   # Unit tests only
poetry run pytest tests/path/to/test.py  # Single test file
poetry run pytest --cov                  # With coverage (must be ≥90%)

# Linting & Formatting
poetry run ruff check .                  # Lint
poetry run ruff check . --fix            # Fix linting issues
poetry run black .                       # Format
poetry run mypy src                      # Type check

# Dependencies
poetry install                           # Install dependencies
poetry lock                              # Update lock file
poetry add package_name                  # Add dependency
```

### Frontend (Next.js + Yarn)
```bash
cd frontend

# Development
yarn dev                    # Start dev server (port 3000)
yarn build                  # Production build
yarn start                  # Start production server

# Testing
yarn test                   # Run all tests
yarn test:watch             # Watch mode

# Linting & Formatting
yarn lint                   # ESLint
yarn lint --fix             # Fix issues
```

## Architecture Overview

```
Frontend (Next.js:3000) → FastAPI (:8000) → LangGraph Graphs
                                           ↓
                                    PostgreSQL (conversations)
                                    Supabase (vector store)
```

## LangGraph Graphs

Two separate graphs defined in `backend/langgraph.json`:
1. **ingestion_graph**: Processes PDFs → embeddings → Supabase vector store
2. **retrieval_graph**: Routes queries → retrieves docs → generates answers

### Ingestion Graph (`backend/src/ingestion_graph/graph.py`)

**Flow**: `START → ingestDocs → END`

**State** (`IndexState`):
```python
class IndexState(TypedDict):
    docs: Annotated[list[Document], reduce_docs]
```

**Node**:
- `ingestDocs`: Loads docs, processes via reducer, adds to vector store, returns `{"docs": "delete"}` to clear state

### Retrieval Graph (`backend/src/retrieval_graph/graph.py`)

**Flow**:
```
START → checkQueryType → [CONDITIONAL ROUTING]
  ├─ route="retrieve" → retrieveDocuments → generateResponse → END
  └─ route="direct"   → directAnswer → END
```

**State** (`AgentState`):
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    route: str  # "retrieve" or "direct"
    documents: Annotated[list[Document], reduce_docs]
```

**Nodes**:
1. `checkQueryType`: Classifies query using RouteSchema structured output
2. `retrieveDocuments`: Fetches from vector store
3. `generateResponse`: Formats docs + generates answer
4. `directAnswer`: Handles simple queries without retrieval

## State Management - reduce_docs Reducer

**Location**: `backend/src/shared/state.py`

**Behavior**:
- **Appends** new docs to existing (doesn't replace)
- **Deduplicates** using metadata["uuid"]
- **Converts** strings/dicts → Documents
- **Clears** on `{"docs": "delete"}`
- **Generates** UUIDs for docs missing them

## Backend Module Structure

### Core Modules

```
backend/src/
├── shared/
│   ├── configuration.py     # BaseConfiguration + ensure functions
│   ├── retrieval.py         # make_retriever() factory
│   ├── utils.py             # load_chat_model() factory
│   ├── state.py             # reduce_docs reducer
│   └── checkpointer.py      # AsyncPostgresSaver singleton
├── ingestion_graph/
│   ├── graph.py             # Ingestion nodes + compilation
│   ├── state.py             # IndexState TypedDict
│   └── configuration.py     # IndexConfiguration
├── retrieval_graph/
│   ├── graph.py             # Retrieval nodes + compilation
│   ├── state.py             # AgentState TypedDict
│   ├── configuration.py     # AgentConfiguration
│   ├── prompts.py           # ChatPromptTemplates
│   └── utils.py             # Graph-specific utilities
├── conversations/
│   ├── routes.py            # FastAPI conversation endpoints
│   ├── repository.py        # PostgreSQL CRUD operations
│   └── models.py            # Pydantic models
└── main.py                  # FastAPI application
```

### Configuration Hierarchy

- `BaseConfiguration`: Core settings (retriever_provider, retriever_k)
- `IndexConfiguration`: Extends base for ingestion
- `AgentConfiguration`: Extends base with query_model, response_model

### Checkpointer (`backend/src/shared/checkpointer.py`)

Singleton AsyncPostgresSaver for conversation persistence:
```python
async def get_checkpointer() -> AsyncPostgresSaver:
    # Returns singleton instance with async lock
    # Uses DATABASE_URL or individual DB_* env vars
```

## FastAPI Endpoints

### Core Endpoints

1. **GET /health** - Health check
2. **POST /api/ingest** - PDF ingestion
   ```python
   # Request: multipart/form-data
   file: UploadFile (PDF)
   threadId: str
   config: JSON string (optional)
   ```
3. **POST /api/chat** - Streaming chat
   ```python
   # Request: JSON
   {
     "message": str,
     "threadId": str,
     "config": dict (optional)
   }
   # Response: Server-Sent Events stream
   ```

### Conversation Management

4. **GET /api/conversations** - List all conversations
5. **POST /api/conversations** - Create conversation
6. **GET /api/conversations/{thread_id}/history** - Get history
7. **DELETE /api/conversations/{thread_id}** - Delete conversation

All conversation endpoints use PostgreSQL via `ConversationRepository`.

## Frontend Integration

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# Optional: LangChain tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT=AI-Document-Assistant
```

### Thread Management

Client-side UUID generation:
```typescript
const uuid = crypto.randomUUID();
setThreadId(uuid);
```

### Configuration Flow

1. Define in `frontend/constants/graphConfigs.ts`:
   ```typescript
   export const retrievalAssistantStreamConfig: AgentConfiguration = {
     queryModel: 'openai/gpt-4o-mini',
     retrieverProvider: 'supabase',
     k: 5,
   };
   ```

2. Pass via API: `config: { configurable: { ...config } }`

3. Access in nodes:
   ```python
   configuration = ensure_agent_configuration(config)
   ```

### API Routes

Next.js routes (`frontend/app/api/`) proxy to FastAPI with IPv4 forcing.

## Database Configuration

### PostgreSQL (Conversations)

Required for conversation persistence:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
# OR individual vars:
DB_HOST=host
DB_PORT=5432
DB_NAME=dbname
DB_USER=user
DB_PASSWORD=pass
```

### Supabase (Vector Store)

Required for document embeddings:
```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
```

## Testing

### Structure
```
backend/tests/
├── ingestion_graph/
├── retrieval_graph/
├── shared/
├── conversations/
├── integration/
├── performance/
└── test_main.py
```

### Requirements
- Coverage must be ≥90% (`--cov-fail-under=90`)
- Use `@pytest.mark.integration` for slow tests
- Skip with: `pytest -m "not integration"`

### Test Patterns
```python
# Mock external dependencies
with patch("src.retrieval_graph.graph.make_retriever") as mock:
    mock.return_value = AsyncMock()
    result = await node(state, config)
```

## Development Workflow

1. **Standard Development**:
   ```bash
   cd backend && poetry run uvicorn src.main:app --reload
   cd frontend && yarn dev
   ```
   Access: http://localhost:3000

2. **Graph Debugging** (optional):
   ```bash
   poetry run langgraph dev  # Port 2024
   ```
   Use LangGraph Studio for visual debugging

## Key Patterns

### Node Functions
```python
async def node_name(state: StateType, config: RunnableConfig) -> dict:
    configuration = ensure_configuration(config)
    # Process and return state updates
    return {"field": "value"}
```

### State Updates
- Append docs: `return {"documents": new_docs}`
- Clear docs: `return {"docs": "delete"}`
- Messages auto-append via `add_messages` reducer

### Graph Compilation
```python
builder = StateGraph(StateType)
builder.add_node("nodeName", node_function)
builder.add_edge(START, "nodeName")
builder.add_conditional_edges("node", route_fn, ["option1", "option2"])
graph = builder.compile()
```

## Common Gotchas

1. **State Reducers**: Returning docs appends (use "delete" to clear)
2. **Thread IDs**: Generated client-side, not server-side
3. **Async/Await**: All nodes must be async
4. **Configuration**: Use ensure_*_configuration() for typed access
5. **Backend**: FastAPI is the ONLY backend needed (LangGraph dev server is optional)

## Git Commit Policy

When creating git commits, do not include the Claude Code marketing footer (no "Generated with Claude Code" or "Co-Authored-By: Claude" lines). Keep commit messages clean and minimal.