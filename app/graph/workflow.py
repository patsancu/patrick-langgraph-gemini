import os
from langgraph.graph import StateGraph, START, END
from app.graph.state import AppState
from app.dependencies import get_ticket_store, get_version_control
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from app.graph.llm_schemas import POExtraction, DevLeadExtraction

# Configure LLM (will require OPENAI_API_KEY in environment)
# Using a fallback to avoid crashing during initialization if key is missing
def get_llm():
    return ChatOpenAI(model="gpt-4o", temperature=0)

def po_agent(state: AppState) -> dict:
    store = get_ticket_store()
    print("--- PO Agent: Analyzing Ticket ---")
    
    ticket_desc = state.get("original_ticket_desc", "")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Using mock PO logic.")
        uc1_id = store.create_ticket(title="Use Case 1: Core feature", description="Extracted from " + state.get("original_ticket_id", ""), ticket_type="use_case")
        uc2_id = store.create_ticket(title="Use Case 2: UI setup", description="Extracted from " + state.get("original_ticket_id", ""), ticket_type="use_case")
        return {"use_case_tickets": [uc1_id, uc2_id], "messages": [AIMessage(content="PO Agent created use cases (mock).")]}

    llm = get_llm().with_structured_output(POExtraction)
    prompt = f"""
    You are the Product Owner for a new software project. 
    Analyze the following user request and break it down into distinct, logical 'Use Cases'.
    
    User Request: {ticket_desc}
    """
    
    result = llm.invoke(prompt)
    use_case_ids = []
    
    for uc in result.use_cases:
        uc_id = store.create_ticket(title=uc.title, description=uc.description, ticket_type="use_case")
        use_case_ids.append(uc_id)
        
    return {"use_case_tickets": use_case_ids, "messages": [AIMessage(content="PO Agent generated use cases via LLM.")]}

def dev_lead_agent(state: AppState) -> dict:
    store = get_ticket_store()
    print("--- Dev Lead Agent: Creating Dev Tasks ---")
    
    dev_tickets = state.get("dev_tickets", [])
    if dev_tickets:
        # Avoid recreating tickets if already populated
        return {}

    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Using mock Dev Lead logic.")
        devops_id = store.create_ticket(title="Scaffold App", description="Setup next.js/supabase", ticket_type="devops")
        fe_id = store.create_ticket(title="Implement UI", description="Implement UI for use cases", ticket_type="frontend")
        be_id = store.create_ticket(title="Implement API", description="Implement API for use cases", ticket_type="backend")
        
        dev_tickets = [
            {"id": devops_id, "type": "devops", "status": "TODO"},
            {"id": fe_id, "type": "frontend", "status": "TODO"},
            {"id": be_id, "type": "backend", "status": "TODO"}
        ]
        return {"dev_tickets": dev_tickets, "messages": [AIMessage(content="Dev Lead assigned tasks (mock).")]}

    # Gather use case details
    uc_details = []
    for uc_id in state.get("use_case_tickets", []):
        ticket = store.get_ticket(uc_id)
        if ticket:
            uc_details.append(f"- {ticket['title']}: {ticket['description']}")
    
    uc_text = "\n".join(uc_details)
    
    llm = get_llm().with_structured_output(DevLeadExtraction)
    prompt = f"""
    You are the Dev Team Lead. You must read the following Use Cases and create specific development tasks to implement them.
    If this is a new feature that needs a full project setup, include a 'devops' task to scaffold the app.
    Include 'frontend' and 'backend' tasks as necessary to fulfill the requirements.
    
    Use Cases:
    {uc_text}
    """
    
    result = llm.invoke(prompt)
    new_dev_tickets = []
    
    for task in result.tasks:
        # Validate task type before creating
        task_type = task.type if task.type in ["frontend", "backend", "devops"] else "backend"
        task_id = store.create_ticket(title=task.title, description=task.description, ticket_type=task_type)
        new_dev_tickets.append({"id": task_id, "type": task_type, "status": "TODO"})
        
    return {"dev_tickets": new_dev_tickets, "messages": [AIMessage(content="Dev Lead generated dev tasks via LLM.")]}

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
