import os
from app.interfaces.ticket_store import MockTicketStore
from app.interfaces.linear_ticket_store import LinearTicketStore
from app.interfaces.version_control import MockVersionControl

# Check for Linear API keys
linear_api_key = os.getenv("LINEAR_API_KEY")
linear_team_id = os.getenv("LINEAR_TEAM_ID")

if linear_api_key and linear_team_id:
    ticket_store = LinearTicketStore(linear_api_key, linear_team_id)
else:
    # Using singleton for mock to maintain state in memory during execution
    ticket_store = MockTicketStore()

version_control = MockVersionControl()

def get_ticket_store():
    return ticket_store

def get_version_control():
    return version_control
