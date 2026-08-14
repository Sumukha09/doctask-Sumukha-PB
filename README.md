# FlowDocs

 **This repository is currently at Step 1 — Foundation.**
Only the backend skeleton, PostgreSQL + pgvector, Alembic migration infrastructure,
Docker Compose orchestration, FastAPI `/health`, and tests are implemented.
LangGraph, LLM integration, frontend, extraction, verification, and orchestration
land in later steps.

## Stack

- **Language**: Python 3.12
- **Web framework**: FastAPI
- **Database**: PostgreSQL 16 with the `pgvector` extension
- **ORM**: SQLAlchemy 2.x with `psycopg[binary]`
- **Migrations**: Alembic (the only migration system)
- **Configuration**: Pydantic Settings
- **Container**: Docker Compose

## Prerequisites

- Docker 24+
- Docker Compose v2
- Python 3.12 (only if running tests on the host instead of inside the container)

## Configuration

Copy `.env.example` to `.env` and edit if needed. Defaults are tuned for local
development and match `docker-compose.yml` out of the box.

```bash
cp .env.example .env
```

## Start the project

```bash
make up
# or: docker compose up -d --build
```

## Apply migrations

```bash
make migrate
# or: docker compose exec backend alembic upgrade head
```

This creates the `alembic_version` table and enables the `pgvector` extension.

## Run tests

```bash
make test
# or: docker compose exec backend pytest -v
```

The test suite uses the running PostgreSQL container. It does not mock the
database and does not call any external API.

## Check health

```bash
make health
# or: curl http://localhost:8000/health
```

A successful response is `{"status":"ok","database":"ok"}`. Anything else means
the backend cannot reach PostgreSQL.

## Stop the project

```bash
make down
# or: docker compose down
```

Volumes are preserved. Use `make clean` to also delete the database volume
(destructive).

## Layout

```
flowdocs/
├── .agents/AGENTS.md           Engineering rules
├── docs/                       Living requirements / design notes
├── backend/                    FastAPI application
│   ├── app/                    Source code
│   ├── alembic/                Migration infrastructure
│   └── tests/                  pytest suite
├── docker-compose.yml          Postgres + backend
├── Makefile                    Common commands
└── .env.example
```

See `.agents/AGENTS.md` for the engineering rules that govern this codebase.

## Machine Context Protocol (MCP) Server

FlowDocs includes a built-in MCP server that allows machine agents (such as Claude Desktop or other AI clients) to interact programmatically with the document processing workflow.

### Starting the MCP Server

You can run the MCP server using standard I/O (stdio) transport:

```bash
cd backend
python run_mcp.py
```

### Available MCP Tools

The server exposes the following tools, which reuse the existing application services safely:
- `create_run(file_paths, compliance_rules)`: Start a new document processing run.
- `get_run(run_id)`: Fetch basic status of a run.
- `get_run_state(run_id)`: Retrieve the granular workflow execution trace.
- `resume_run(run_id)`: Resume a stalled or failed workflow run.
- `add_documents(run_id, file_paths)`: Incrementally add new documents to a run without starting over.
- `get_findings(run_id)`: List all compliance findings for a run.
- `review_finding(run_id, finding_id, decision, comment)`: Programmatically approve/reject a finding.
- `get_report(run_id)`: Retrieve the final compliance report metadata.

### Example Machine-Driven Workflow

1. Start a run: `create_run(file_paths=["/absolute/path/to/doc.pdf"])`
2. Poll the state: `get_run_state(run_id="<id>")`
3. If human approval is reached, fetch findings: `get_findings(run_id="<id>")`
4. Programmatically approve a finding: `review_finding(run_id="<id>", finding_id="<f_id>", decision="approve")`
5. The workflow automatically resumes.
6. Retrieve the final deliverable: `get_report(run_id="<id>")`
