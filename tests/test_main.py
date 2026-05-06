from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_webhook_ticket():
    response = client.post("/webhook/ticket", json={"title": "Test Ticket", "description": "Test Desc"})
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    assert "ticket_id" in data
    assert data["message"] == "Workflow started"

def test_get_status_not_found():
    response = client.get("/workflow/invalid-thread-id/status")
    assert response.status_code == 404

def test_human_input_not_found():
    response = client.post("/workflow/invalid-thread-id/human-input", json={"clarification": "test"})
    assert response.status_code == 400
