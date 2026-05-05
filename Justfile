default:
    just --list

# Install Python dependencies
install:
	uv sync

# Run the FastAPI development server
dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test the webhook endpoint with a mock ticket
test-webhook:
	curl -X POST "http://localhost:8000/webhook/ticket" \
		-H "Content-Type: application/json" \
		-d '{"title": "Implement login", "description": "Create a login page using next auth"}'

# Check the status of a specific workflow thread
# Usage: just status <thread_id>
status thread_id:
	curl -X GET "http://localhost:8000/workflow/{{thread_id}}/status"

# Provide human input to resume a workflow
# Usage: just human-input <thread_id> "My clarification"
human-input thread_id clarification:
	curl -X POST "http://localhost:8000/workflow/{{thread_id}}/human-input" \
		-H "Content-Type: application/json" \
		-d '{"clarification": "{{clarification}}"}'
