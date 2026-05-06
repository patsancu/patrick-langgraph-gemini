import operator
from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage

class AppState(TypedDict):
    original_ticket_id: str
    original_ticket_desc: str
    use_case_tickets: List[str]
    # Structure: [{"id": str, "type": "frontend"|"backend"|"devops", "status": "TODO"|"DONE"}]
    dev_tickets: List[dict]
    messages: Annotated[List[BaseMessage], operator.add]
    needs_human_input: bool
    human_clarification: str
