from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ITicketStore(ABC):
    @abstractmethod
    def create_ticket(self, title: str, description: str, ticket_type: str = "feature") -> str:
        pass

    @abstractmethod
    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        pass

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_comment(self, ticket_id: str, comment: str) -> None:
        pass

class MockTicketStore(ITicketStore):
    def __init__(self):
        self.tickets: Dict[str, Dict[str, Any]] = {}
        self.next_id = 1

    def create_ticket(self, title: str, description: str, ticket_type: str = "feature") -> str:
        ticket_id = f"TICK-{self.next_id}"
        self.next_id += 1
        self.tickets[ticket_id] = {
            "id": ticket_id,
            "title": title,
            "description": description,
            "type": ticket_type,
            "status": "TODO",
            "comments": []
        }
        logger.info(f"[MockTicketStore] Created ticket {ticket_id}: {title}")
        return ticket_id

    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        if ticket_id in self.tickets:
            self.tickets[ticket_id]["status"] = status
            logger.info(f"[MockTicketStore] Updated ticket {ticket_id} status to {status}")
        else:
            logger.error(f"[MockTicketStore] Error: Ticket {ticket_id} not found")

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        return self.tickets.get(ticket_id)

    def add_comment(self, ticket_id: str, comment: str) -> None:
        if ticket_id in self.tickets:
            self.tickets[ticket_id]["comments"].append(comment)
            logger.info(f"[MockTicketStore] Added comment to {ticket_id}: {comment}")
        else:
            logger.error(f"[MockTicketStore] Error: Ticket {ticket_id} not found")
