from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import sqlite3
import logging
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from app.graph.workflow import builder
from app.dependencies import get_ticket_store

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LangGraph Autonomous Dev Team API",
    openapi_url="/open-api"
)

# Setup SQLite connection for checkpointer
conn = sqlite3.connect("langgraph_state.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
checkpointer.setup()

# Compile the graph with checkpointer and interrupt before human_input
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_input"]
)

class TicketRequest(BaseModel):
    title: str
    description: str

class HumanClarificationRequest(BaseModel):
    clarification: str

@app.post("/webhook/ticket")
def create_ticket(request: TicketRequest):
    store = get_ticket_store()
    ticket_id = store.create_ticket(request.title, request.description, ticket_type="feature")
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initial state
    initial_state = {
        "original_ticket_id": ticket_id,
        "original_ticket_desc": request.description,
        "use_case_tickets": [],
        "dev_tickets": [],
        "messages": [],
        "needs_human_input": False,
        "human_clarification": ""
    }
    
    # Run graph in a background task or await (synchronous for simplicity here)
    # Ideally, this should be an async execution if agents make actual API calls.
    # Because we're using mock sync operations, we can just invoke it.
    try:
        graph.invoke(initial_state, config)
    except Exception as e:
        logger.error(f"Graph execution paused or error: {e}")
        
    return {"message": "Workflow started", "thread_id": thread_id, "ticket_id": ticket_id}

@app.get("/workflow/{thread_id}/status")
def get_status(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = graph.get_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found")
        
    next_node = state_snapshot.next
    values = state_snapshot.values
    
    return {
        "thread_id": thread_id,
        "next_node": next_node,
        "state_values": values
    }

@app.post("/workflow/{thread_id}/human-input")
def provide_human_input(thread_id: str, request: HumanClarificationRequest):
    config = {"configurable": {"thread_id": thread_id}}
    
    state_snapshot = graph.get_state(config)
    if not state_snapshot or "human_input" not in state_snapshot.next:
        raise HTTPException(status_code=400, detail="Graph is not waiting for human input")
        
    # Update the state as if the human_input node executed it
    # We resume the graph by passing the new state to the human_input node or just bypassing it
    # For now, let's update state and continue
    updated_state = {"human_clarification": request.clarification, "needs_human_input": False}
    
    try:
        graph.invoke(updated_state, config)
    except Exception as e:
        logger.error(f"Graph execution paused or error: {e}")
        
    return {"message": "Graph resumed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_config="log_config.yaml")
