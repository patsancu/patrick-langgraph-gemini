from langgraph.graph import StateGraph, START, END
from app.graph.state import AppState
from app.dependencies import get_ticket_store, get_version_control
from langchain_core.messages import AIMessage

def po_agent(state: AppState) -> dict:
    store = get_ticket_store()
    print("--- PO Agent: Analyzing Ticket ---")
    
    # Mock LLM logic: Breaking into 2 use cases
    uc1_id = store.create_ticket(title="Use Case 1: Core feature", description="Extracted from " + state.get("original_ticket_id", ""), ticket_type="use_case")
    uc2_id = store.create_ticket(title="Use Case 2: UI setup", description="Extracted from " + state.get("original_ticket_id", ""), ticket_type="use_case")
    
    return {"use_case_tickets": [uc1_id, uc2_id], "messages": [AIMessage(content="PO Agent created use cases.")]}

def dev_lead_agent(state: AppState) -> dict:
    store = get_ticket_store()
    print("--- Dev Lead Agent: Creating Dev Tasks ---")
    
    dev_tickets = state.get("dev_tickets", [])
    if not dev_tickets:
        # Initial task creation
        devops_id = store.create_ticket(title="Scaffold App", description="Setup next.js/supabase", ticket_type="devops")
        fe_id = store.create_ticket(title="Implement UI", description="Implement UI for use cases", ticket_type="frontend")
        be_id = store.create_ticket(title="Implement API", description="Implement API for use cases", ticket_type="backend")
        
        dev_tickets = [
            {"id": devops_id, "type": "devops", "status": "TODO"},
            {"id": fe_id, "type": "frontend", "status": "TODO"},
            {"id": be_id, "type": "backend", "status": "TODO"}
        ]
        return {"dev_tickets": dev_tickets, "messages": [AIMessage(content="Dev Lead assigned tasks.")]}
    return {}

def devops_agent(state: AppState) -> dict:
    store = get_ticket_store()
    vc = get_version_control()
    print("--- DevOps Agent: Scaffolding ---")
    
    dev_tickets = state.get("dev_tickets", [])
    updated_tickets = []
    
    for t in dev_tickets:
        if t["type"] == "devops" and t["status"] == "TODO":
            branch = vc.create_branch(f"devops-{t['id']}")
            vc.commit_code(branch, "Initial scaffold", {"package.json": "{}"})
            pr = vc.create_pull_request("Scaffold PR", "Added scaffold", branch)
            store.update_ticket_status(t['id'], "DONE")
            t["status"] = "DONE"
            store.add_comment(t['id'], f"PR created: {pr}")
        updated_tickets.append(t)
        
    return {"dev_tickets": updated_tickets, "messages": [AIMessage(content="DevOps completed scaffolding.")]}

def developer_agent(state: AppState) -> dict:
    store = get_ticket_store()
    vc = get_version_control()
    print("--- Developer Agent: Coding ---")
    
    dev_tickets = state.get("dev_tickets", [])
    updated_tickets = []
    
    for t in dev_tickets:
        if t["type"] in ["frontend", "backend"] and t["status"] == "TODO":
            branch = vc.create_branch(f"dev-{t['id']}")
            vc.commit_code(branch, "Implemented feature", {"code.ts": "// code"})
            pr = vc.create_pull_request(f"{t['type']} feature PR", "Implemented code", branch)
            store.update_ticket_status(t['id'], "DONE")
            t["status"] = "DONE"
            store.add_comment(t['id'], f"PR created: {pr}")
        updated_tickets.append(t)
        
    return {"dev_tickets": updated_tickets, "messages": [AIMessage(content="Devs completed tasks.")]}

def qa_agent(state: AppState) -> dict:
    print("--- QA Agent: Reviewing ---")
    vc = get_version_control()
    # Mock QA just merges all open PRs in theory
    # For now, just mark state as completed.
    return {"messages": [AIMessage(content="QA Agent approved and merged PRs.")]}

def human_input(state: AppState) -> dict:
    print("--- Human Input Required ---")
    # This node simply acts as an interrupt point. State update happens via API.
    return {"needs_human_input": False}

# Router Logic
def route_after_dev_lead(state: AppState) -> str:
    dev_tickets = state.get("dev_tickets", [])
    if any(t["type"] == "devops" and t["status"] == "TODO" for t in dev_tickets):
        return "devops_agent"
    return "developer_agent"

def route_after_devs(state: AppState) -> str:
    # If all dev tasks done, go to QA
    dev_tickets = state.get("dev_tickets", [])
    if all(t["status"] == "DONE" for t in dev_tickets if t["type"] in ["frontend", "backend"]):
        return "qa_agent"
    # Wait for human or loop back if errors (simplified for now)
    return "qa_agent"

# Build Graph
builder = StateGraph(AppState)

builder.add_node("po_agent", po_agent)
builder.add_node("dev_lead_agent", dev_lead_agent)
builder.add_node("devops_agent", devops_agent)
builder.add_node("developer_agent", developer_agent)
builder.add_node("qa_agent", qa_agent)
builder.add_node("human_input", human_input)

builder.add_edge(START, "po_agent")
builder.add_edge("po_agent", "dev_lead_agent")

builder.add_conditional_edges("dev_lead_agent", route_after_dev_lead)

# DevOps output loops back to Dev Lead to re-evaluate what tasks are ready
builder.add_edge("devops_agent", "dev_lead_agent") 

builder.add_conditional_edges("developer_agent", route_after_devs)
builder.add_edge("qa_agent", END)

# Add interrupt before human input
# We'll configure checkpointer and memory in the main application instance
