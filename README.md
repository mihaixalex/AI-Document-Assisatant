# AI PDF Chatbot

LangGraph-based RAG chatbot that ingests PDFs into Supabase vector store and answers queries using OpenAI.

## Table of Contents

1. [Features](#features)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Running Locally](#running-locally)
7. [Database](#database)
8. [API](#api)
9. [Quality](#quality)
10. [CI/CD](#cicd)
11. [Security Notes](#security-notes)
12. [Troubleshooting](#troubleshooting)
13. [License](#license)

## Features

**AI-Powered Document Q&A**
- Upload multiple PDF files (up to 5 files, 10MB each) and ask questions about their content
- Intelligent query routing: Direct answers for simple questions, retrieval-augmented generation for document-specific queries
- Streaming responses for real-time conversational experience

**Built on Modern AI Stack**
- **LangGraph State Graphs**: Two separate graphs for ingestion and retrieval workflows
- **Vector Search**: Supabase vector store with pgvector for semantic search
- **OpenAI Integration**: GPT-4o-mini for embeddings and response generation
- **LangSmith Tracing**: Optional observability for debugging and monitoring

**Developer Experience**
- Hot reload with LangGraph dev server and Next.js dev mode
- LangGraph Studio UI for visual graph debugging
- Comprehensive test suite with mocking patterns
- Type safety with TypeScript and Python type hints

## Quick Start

**Prerequisites**: Node.js 18+, Python 3.11+, Poetry, Yarn, Supabase account, OpenAI API key

```bash
# 1. Clone and install
git clone https://github.com/mayooear/ai-document-assistant.git
cd ai-document-assistant
yarn install
cd backend && poetry install && cd ..

# 2. Configure backend
cp backend/.env.example backend/.env
# Edit backend/.env with your OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# 3. Configure frontend
cp frontend/.env.example frontend/.env
# Edit if needed (defaults work for local dev)

# 4. Set up Supabase
# Create table `documents` and function `match_documents` per:
# https://python.langchain.com/docs/integrations/vectorstores/supabase/

# 5. Start backend (terminal 1)
cd backend && poetry run langgraph dev

# 6. Start frontend (terminal 2)
cd frontend && yarn dev

# 7. Open http://localhost:3000
```

## Architecture

```mermaid
flowchart LR
    U[User] -->|Upload PDF| F[Frontend :3000]
    F -->|POST /api/ingest| I[Ingestion Graph]
    I -->|Embed & store| S[(Supabase)]

    U -->|Ask question| F
    F -->|POST /api/chat SSE| R[Retrieval Graph]
    R -->|Query| S
    S -->|Docs| R
    R -->|LLM response| O[OpenAI]
    O -->|Answer stream| F

    I -.runs on.-> B[LangGraph :2024]
    R -.runs on.-> B
```

**Components**
- **Frontend**: Next.js 14 React app with PDF upload and chat UI
- **Backend**: Python LangGraph service with two state graphs
  - `ingestion_graph`: Processes PDFs → embeddings → Supabase
  - `retrieval_graph`: Routes query → retrieves docs → generates answer
- **Vector Store**: Supabase with `documents` table and `match_documents` function
- **LLM**: OpenAI GPT-4o-mini (configurable in `frontend/constants/graphConfigs.ts`)

**Retrieval Graph Flow**

```mermaid
flowchart TD
    Start([Query]) --> Check[checkQueryType]
    Check -->|retrieve| Retrieve[retrieveDocuments]
    Check -->|direct| Direct[directAnswer]
    Retrieve --> Generate[generateResponse]
    Generate --> End([Response])
    Direct --> End
```

## Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── ingestion_graph/    # PDF indexing graph
│   │   │   ├── graph.py        # Graph: ingestDocs node
│   │   │   ├── state.py        # IndexState definition
│   │   │   └── configuration.py
│   │   ├── retrieval_graph/    # Q&A graph
│   │   │   ├── graph.py        # Graph: 4 nodes with routing
│   │   │   ├── state.py        # AgentState definition
│   │   │   ├── prompts.py      # Router & response prompts
│   │   │   ├── utils.py        # Doc formatting helpers
│   │   │   └── configuration.py
│   │   ├── shared/             # Shared utilities
│   │   │   ├── configuration.py # BaseConfiguration
│   │   │   ├── retrieval.py    # make_retriever factory
│   │   │   ├── state.py        # reduce_docs reducer
│   │   │   └── utils.py        # load_chat_model
│   │   ├── health.py           # Health check endpoint
│   │   └── sample_docs.json    # Demo data
│   ├── tests/                  # pytest suite (90% coverage target)
│   ├── pyproject.toml          # Poetry config
│   ├── langgraph.json          # Graph endpoint definitions
│   └── Dockerfile              # Production image
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── ingest/route.ts # PDF upload handler
│   │   │   └── chat/route.ts   # SSE streaming handler
│   │   ├── page.tsx            # Chat UI
│   │   └── layout.tsx
│   ├── components/             # React + shadcn/ui
│   ├── lib/
│   │   ├── langgraph-server.ts # Backend SDK (server-side)
│   │   ├── langgraph-client.ts # Backend SDK (client-side)
│   │   └── pdf.ts              # PDF parsing
│   └── constants/graphConfigs.ts # Graph defaults (model, k, provider)
└── .github/workflows/ci.yml    # CI: format + lint
```

## Configuration

**Environment Variables**

Backend (`.env` in `backend/`):

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| OPENAI_API_KEY | Yes | OpenAI API key | sk-... |
| SUPABASE_URL | Yes | Supabase project URL | https://xxx.supabase.co |
| SUPABASE_SERVICE_ROLE_KEY | Yes | Supabase service role key | eyJh... |
| LANGCHAIN_TRACING_V2 | No | Enable LangSmith tracing | true |
| LANGCHAIN_API_KEY | No | LangSmith API key | lsv2_... |
| LANGCHAIN_PROJECT | No | LangSmith project name | ai-pdf-chatbot |

Frontend (`.env.local` in `frontend/`):

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| NEXT_PUBLIC_LANGGRAPH_API_URL | No | Backend URL | http://127.0.0.1:2024 |
| LANGGRAPH_INGESTION_ASSISTANT_ID | No | Ingestion graph ID | ingestion_graph |
| LANGGRAPH_RETRIEVAL_ASSISTANT_ID | No | Retrieval graph ID | retrieval_graph |
| LANGCHAIN_API_KEY | No | LangSmith API key | |
| LANGCHAIN_TRACING_V2 | No | Enable tracing | true |
| LANGCHAIN_PROJECT | No | Project name | AI-Document-Assistant |

**Ports and URLs**
- Backend LangGraph server: `http://localhost:2024`
- Frontend dev server: `http://localhost:3000`
- LangGraph Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
- API Documentation: `http://localhost:2024/docs`

## Running Locally

**Native (recommended for development)**

Terminal 1 - Backend:
```bash
cd backend
poetry install
poetry run langgraph dev
```

Terminal 2 - Frontend:
```bash
cd frontend
yarn install
yarn dev
```

Access:
- Chat UI: http://localhost:3000
- LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- API Docs: http://localhost:2024/docs

**Docker (backend only)**

```bash
cd backend
docker build -t pdf-chatbot-backend .
docker run -p 2024:2024 --env-file .env pdf-chatbot-backend
```

Note: No docker-compose provided. Frontend deployment via Vercel/Netlify recommended.

## Database

**Supabase Setup**

Required table and function for vector search:

```sql
-- Table: documents
CREATE TABLE documents (
  id BIGSERIAL PRIMARY KEY,
  content TEXT,
  metadata JSONB,
  embedding VECTOR(1536)
);

-- Function: match_documents
CREATE FUNCTION match_documents (
  query_embedding VECTOR(1536),
  match_count INT DEFAULT 5,
  filter JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE (
  id BIGINT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
#variable_conflict use_column
BEGIN
  RETURN QUERY
  SELECT
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE metadata @> filter
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

For detailed setup: https://js.langchain.com/docs/integrations/vectorstores/supabase/

**Migrations**: None. Manual SQL setup required above.

**Seeding**: Use demo data via backend config `useSampleDocs: true` in `frontend/constants/graphConfigs.ts`

## API

**Endpoints**

- `POST /api/ingest` - Upload PDFs (max 5 files, 10MB each)
  - Request: `multipart/form-data` with `files` field
  - Response: `{ message, threadId }`

- `POST /api/chat` - Query chatbot (SSE stream)
  - Request: `{ message: string, threadId: string }`
  - Response: Server-Sent Events with LangGraph chunks

**Example: Upload PDF**

```bash
curl -X POST http://localhost:3000/api/ingest \
  -F "files=@document.pdf"
```

**Example: Ask Question**

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the main topic?", "threadId": "abc123"}'
```

**OpenAPI**: Not available. LangGraph Studio provides graph visualization.

## Quality

**Linting and Formatting**

```bash
# Root (all workspaces)
yarn lint              # Check all
yarn lint:fix          # Fix all
yarn format            # Format all
yarn format:check      # Check format

# Backend
cd backend
poetry run ruff check .        # Lint
poetry run ruff check . --fix  # Fix
poetry run black .             # Format
poetry run mypy src            # Type check

# Frontend
cd frontend
yarn lint              # ESLint
yarn lint --fix        # Fix
```

**Testing**

```bash
# Backend
cd backend
poetry run pytest                    # All tests
poetry run pytest -m "not integration"  # Unit only
poetry run pytest --cov              # With coverage
poetry run pytest --cov-report=html  # HTML report

# Frontend
cd frontend
yarn test              # All tests
yarn test:watch        # Watch mode
```

**Pre-commit Hooks**: None configured. TODO: Add husky/lint-staged.

**Coverage Targets**
- Backend: 90% (enforced in pytest config)
- Frontend: No target set

## CI/CD

**GitHub Actions** (`.github/workflows/ci.yml`)

Runs on: Push to main, PRs, manual trigger

Jobs:
1. **format** - Checks code formatting with `yarn format:check`
2. **lint** - Lints code with `yarn run lint:all`

**Missing**:
- Test execution (pytest and jest)
- Backend validation
- Deployment workflow

**Deploy Backend**

Option 1 - LangGraph Cloud:
```bash
# Follow: https://langchain-ai.github.io/langgraph/cloud/quick_start/
```

Option 2 - Self-hosted:
```bash
cd backend
docker build -t pdf-chatbot .
docker push your-registry/pdf-chatbot
# Deploy to your infrastructure
```

**Deploy Frontend**

Vercel (recommended):
```bash
cd frontend
vercel --prod
```

Set env vars in Vercel dashboard:
- `NEXT_PUBLIC_LANGGRAPH_API_URL` = your deployed backend URL
- `LANGGRAPH_INGESTION_ASSISTANT_ID` = ingestion_graph
- `LANGGRAPH_RETRIEVAL_ASSISTANT_ID` = retrieval_graph

## Security Notes

- **Authentication**: None. `/api/ingest` and `/api/chat` are public endpoints.
- **CORS**: Frontend API routes run server-side; no CORS issues.
- **Rate Limiting**: None. Add rate-limiting middleware before production.
- **API Keys**: Stored in `.env` files. Never commit `.env` to git.
- **File Upload**: Limited to 5 PDFs, 10MB each (configurable in `app/api/ingest/route.ts`)
- **Secrets**: LangChain API key is optional but recommended for debugging.

TODO: Add authentication (e.g., NextAuth.js) and rate limiting (e.g., upstash/ratelimit).

## Troubleshooting

**1. `OPENAI_API_KEY not set`**
```
Error: OpenAI API key not found
Fix: Copy backend/.env.example to backend/.env and add your key
```

**2. `SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not defined`**
```
Error: Supabase credentials missing
Fix: Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to backend/.env
Check: Verify credentials at https://app.supabase.com/project/_/settings/api
```

**3. `match_documents function does not exist`**
```
Error: function match_documents(vector, integer, jsonb) does not exist
Fix: Run the SQL from "Database" section above in Supabase SQL editor
```

**4. `poetry: command not found`**
```
Error: poetry not installed
Fix: Install Poetry: curl -sSL https://install.python-poetry.org | python3 -
     Or: brew install poetry (macOS)
```

**5. `poetry.lock` out of sync**
```
Error: pyproject.toml changed significantly since poetry.lock was last generated
Fix: cd backend && poetry lock && poetry install
```

**6. `langgraph: command not found` or `Required package 'langgraph-api' is not installed`**
```
Error: Command not found: langgraph
       Or: Required package 'langgraph-api' is not installed
Fix: cd backend && poetry lock && poetry install
     (Ensures langgraph-cli[inmem] is installed from updated pyproject.toml)
```

**7. `Port 2024 already in use`**
```
Error: Address already in use
Fix: Kill process: lsof -ti:2024 | xargs kill -9
     Or: Change port in langgraph.json and NEXT_PUBLIC_LANGGRAPH_API_URL
```

**8. Frontend can't connect to backend**
```
Error: Failed to fetch from http://localhost:2024
Fix: Ensure backend is running (poetry run langgraph dev)
     Verify NEXT_PUBLIC_LANGGRAPH_API_URL in frontend/.env.local
```

**9. PDF upload fails silently**
```
Error: No documents extracted
Fix: Check PDF is not encrypted or image-only
     Check backend logs for errors
     Verify file size < 10MB
```

**10. Tests fail with import errors**
```
Error: ModuleNotFoundError: No module named 'src'
Fix: Run from backend/ directory: poetry run pytest
     Ensure poetry install was successful
```

**11. `yarn install` fails**
```
Error: Integrity check failed
Fix: Delete node_modules and yarn.lock, then yarn install
     Or: yarn install --ignore-engines
```

**12. LangGraph Studio doesn't open**
```
Error: Studio UI not launching
Fix: Open manually at https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
     Or check API docs at http://localhost:2024/docs
```

## License

MIT License - See LICENSE file


