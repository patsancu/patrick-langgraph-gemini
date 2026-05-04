from app.interfaces.ticket_store import MockTicketStore
from app.interfaces.version_control import MockVersionControl

# Using singletons for mocks to maintain state in memory during execution
ticket_store = MockTicketStore()
version_control = MockVersionControl()

def get_ticket_store():
    return ticket_store

def get_version_control():
    return version_control
