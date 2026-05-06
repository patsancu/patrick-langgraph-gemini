from app.interfaces.ticket_store import MockTicketStore
from app.interfaces.version_control import MockVersionControl

def test_mock_ticket_store():
    store = MockTicketStore()
    ticket_id = store.create_ticket("Title", "Desc")
    assert ticket_id == "TICK-1"
    
    ticket = store.get_ticket(ticket_id)
    assert ticket["title"] == "Title"
    assert ticket["status"] == "TODO"
    
    store.update_ticket_status(ticket_id, "DONE")
    ticket = store.get_ticket(ticket_id)
    assert ticket["status"] == "DONE"
    
    # Test error cases
    store.update_ticket_status("TICK-999", "DONE")
    store.add_comment("TICK-999", "Comment")
    assert store.get_ticket("TICK-999") is None
    
    store.add_comment(ticket_id, "Comment")
    ticket = store.get_ticket(ticket_id)
    assert "Comment" in ticket["comments"]

def test_mock_version_control():
    vc = MockVersionControl()
    branch = vc.create_branch("feature-1")
    assert branch == "feature-1"
    
    vc.commit_code(branch, "message", {"file.py": "content"})
    
    pr = vc.create_pull_request("Title", "Desc", branch)
    assert pr == "PR-feature-1"
    
    vc.merge_pull_request(pr)
