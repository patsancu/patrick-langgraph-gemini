import json
from unittest.mock import patch, MagicMock
from app.interfaces.linear_ticket_store import LinearTicketStore

def test_linear_create_ticket():
    store = LinearTicketStore("api_key", "team_id")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "issueCreate": {
                "issue": {
                    "id": "uuid-1",
                    "identifier": "TEAM-1",
                    "title": "Title"
                }
            }
        }
    }

    with patch("requests.post", return_value=mock_response) as mock_post:
        issue_id = store.create_ticket("Title", "Desc")
        assert issue_id == "uuid-1"

        # Test error handling
        mock_response.json.return_value = {"errors": [{"message": "error"}]}
        issue_id_error = store.create_ticket("Title", "Desc")
        assert issue_id_error == ""

def test_linear_get_ticket():
    store = LinearTicketStore("api_key", "team_id")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "issue": {
                "id": "uuid-1",
                "title": "Title",
                "state": {"type": "completed"}
            }
        }
    }

    with patch("requests.post", return_value=mock_response):
        issue = store.get_ticket("uuid-1")
        assert issue is not None
        assert issue["status"] == "DONE"
        assert issue["type"] == "feature"

        # Test started
        mock_response.json.return_value["data"]["issue"]["state"]["type"] = "started"
        issue = store.get_ticket("uuid-1")
        assert issue["status"] == "IN PROGRESS"

        # Test unstarted
        mock_response.json.return_value["data"]["issue"]["state"]["type"] = "unstarted"
        issue = store.get_ticket("uuid-1")
        assert issue["status"] == "TODO"

        # Test None
        mock_response.json.return_value = {"data": {"issue": None}}
        assert store.get_ticket("uuid-invalid") is None

def test_linear_update_ticket():
    store = LinearTicketStore("api_key", "team_id")

    # First call is state caching, second is update
    mock_states = {"data": {"team": {"states": {"nodes": [{"id": "state-1", "type": "completed"}]}}}}
    mock_update = {"data": {"issueUpdate": {"success": True}}}

    mock_response = MagicMock()
    mock_response.json.side_effect = [mock_states, mock_update, mock_states, {"errors": ["err"]}]

    with patch("requests.post", return_value=mock_response):
        # Update should work
        store.update_ticket_status("uuid-1", "DONE")
        assert store._states_cache["completed"] == "state-1"

        # Trigger an error
        store.update_ticket_status("uuid-1", "DONE")

    # Invalid status should return safely without post for update
    store._states_cache.clear()
    mock_response.json.side_effect = [mock_states]
    with patch("requests.post", return_value=mock_response):
        store.update_ticket_status("uuid-1", "INVALID")

def test_linear_add_comment():
    store = LinearTicketStore("api_key", "team_id")

    mock_response = MagicMock()
    mock_response.json.side_effect = [{"data": {"commentCreate": {"success": True}}}, {"errors": ["err"]}]

    with patch("requests.post", return_value=mock_response):
        store.add_comment("uuid-1", "comment")
        store.add_comment("uuid-1", "comment")
