# LangGraph Autonomous Dev Team API

An orchestration API built with LangGraph and FastAPI that simulates a full software development team. It autonomously manages and executes product development workflows from a Linear ticket to a deployed application.

## Overview

This project provides a backend service that orchestrates a team of AI agents:
- **Product Owner (PO) Agent:** Analyzes user tickets and breaks them down into distinct use cases.
- **Dev Team Lead Agent:** Analyzes technical requirements and delegates tasks (Frontend, Backend, DevOps).
- **DevOps Agent:** Scaffolds new applications or performs infrastructure checkups. (Currently scaffolds applications using the mandatory stack: Next.js, Tailwind CSS, Supabase).
- **Developer Agents (Frontend/Backend):** Implement code and create pull requests.
- **QA / Human Review Agent:** Reviews work and merges PRs.

The orchestration ensures tasks are executed in the correct order, handling dependencies like ensuring the DevOps scaffold is complete before developers start coding.

## Running Locally

### Prerequisites
- Python 3.10+
- `uv` package manager
- `just` command runner (optional, but recommended)

### Installation
1. Clone the repository and navigate into it.
2. Install the dependencies using `uv`:
   ```bash
   uv sync
   ```

### Configuration
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Configure your environment variables in `.env`:
   - `OPENAI_API_KEY`: Required for the LLM agents to function properly. If omitted, the application will safely fallback to mock PO and Dev Lead behavior for testing the orchestration graph.
   - *Supabase configuration*: Note that while this backend does not directly connect to Supabase, the DevOps agent scaffolds frontend projects that require Supabase. Thus, your scaffolded frontend applications will need their own Supabase environment variables configured.

### Running the App
Start the development server using Uvicorn (or `just dev`):
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Debugging & Testing
You can test the workflow locally using the provided webhook endpoint. If you don't have an `OPENAI_API_KEY`, the agents will use dummy data, allowing you to debug the graph traversal.

Trigger a mock ticket:
```bash
curl -X POST "http://localhost:8000/webhook/ticket" \
     -H "Content-Type: application/json" \
     -d '{"title": "Implement login", "description": "Create a login page"}'
```

## Library Justifications

The following external libraries are used in this project:

- `fastapi` -> For building the high-performance webhook and status API endpoints, see module `app/main.py`.
- `uvicorn` -> For serving the FastAPI application locally and in production, see module `app/main.py`.
- `langgraph` -> For stateful, multi-agent orchestration and workflow management, see module `app/graph/workflow.py`.
- `langchain` -> For managing LLM prompts and core AI interactions, see module `app/graph/workflow.py`.
- `langchain-openai` -> For integrating OpenAI's GPT models into the agents, see module `app/graph/workflow.py`.
- `pydantic` -> For data validation, request parsing, and LLM structured output schemas, see module `app/graph/llm_schemas.py`.
- `python-dotenv` -> For securely loading environment variables like API keys from a `.env` file, see module `app/main.py`.
- `langgraph-checkpoint-sqlite` -> For persisting LangGraph state to an SQLite database, enabling human-in-the-loop pauses, see module `app/main.py`.
