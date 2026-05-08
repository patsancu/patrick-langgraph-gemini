from app.graph.workflow import po_agent, dev_lead_agent, devops_agent, developer_agent, qa_agent, human_input, route_after_dev_lead, route_after_devs
from unittest.mock import patch
import os

def test_po_agent_mock():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}, clear=True):
        state = {"original_ticket_desc": "Test", "original_ticket_id": "TICK-1"}
        res = po_agent(state)
        assert "use_case_tickets" in res
        assert len(res["use_case_tickets"]) == 2
        assert "messages" in res

def test_dev_lead_agent_mock():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}, clear=True):
        state = {"dev_tickets": []}
        res = dev_lead_agent(state)
        assert "dev_tickets" in res
        assert len(res["dev_tickets"]) == 3
        
        # Test avoid recreating
        state2 = {"dev_tickets": [{"id": "t1"}]}
        res2 = dev_lead_agent(state2)
        assert res2 == {}

def test_devops_agent():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}, clear=True):
        state = {"dev_tickets": [
            {"id": "TICK-1", "type": "devops", "status": "TODO"},
            {"id": "TICK-2", "type": "frontend", "status": "TODO"}
        ]}
        res = devops_agent(state)
        assert res["dev_tickets"][0]["status"] == "DONE"
        assert res["dev_tickets"][1]["status"] == "TODO"

def test_developer_agent():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown"}, clear=True):
        state = {"dev_tickets": [
            {"id": "TICK-1", "type": "devops", "status": "TODO"},
            {"id": "TICK-2", "type": "frontend", "status": "TODO"},
            {"id": "TICK-3", "type": "backend", "status": "TODO"}
        ]}
        res = developer_agent(state)
        assert res["dev_tickets"][0]["status"] == "TODO"
        assert res["dev_tickets"][1]["status"] == "DONE"
        assert res["dev_tickets"][2]["status"] == "DONE"

def test_qa_agent():
    res = qa_agent({})
    assert "messages" in res

def test_human_input():
    res = human_input({})
    assert res["needs_human_input"] is False

def test_route_after_dev_lead():
    state1 = {"dev_tickets": [{"type": "devops", "status": "TODO"}]}
    assert route_after_dev_lead(state1) == "devops_agent"
    
    state2 = {"dev_tickets": [{"type": "frontend", "status": "TODO"}]}
    assert route_after_dev_lead(state2) == "developer_agent"

def test_route_after_devs():
    state1 = {"dev_tickets": [{"type": "frontend", "status": "DONE"}, {"type": "backend", "status": "DONE"}]}
    assert route_after_devs(state1) == "qa_agent"
    
    state2 = {"dev_tickets": [{"type": "frontend", "status": "TODO"}]}
    assert route_after_devs(state2) == "qa_agent" # Current implementation just returns qa_agent
