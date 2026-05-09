import logging
from langgraph.graph import StateGraph, START, END
from app.graph.state import AppState
from app.dependencies import get_ticket_store, get_version_control
from langchain_core.messages import AIMessage
from app.graph.llm_schemas import POSelection, DevLeadExtraction, DevOpsExtraction
from app.llm import get_llm, is_llm_configured
from app.config.prompts import PO_AGENT_PROMPT, DEV_LEAD_AGENT_PROMPT, DEVOPS_AGENT_PROMPT

logger = logging.getLogger(__name__)

def po_agent(state: AppState) -> dict:
    store = get_ticket_store()
    logger.info("--- PO Agent: Grooming Backlog ---")

    backlog_tickets = store.get_tickets_by_status("BACKLOG")
    
    if not backlog_tickets:
        logger.info("No backlog tickets found.")
        return {"use_case_tickets": [], "messages": [AIMessage(content="PO Agent: No backlog tickets to process.")]}

    if not is_llm_configured():
        logger.warning("LLM provider not configured. Using mock PO logic.")
        import random
        # Pick 20% or less, at least 1
        num_to_pick = max(1, int(len(backlog_tickets) * 0.2))
        selected = random.sample(backlog_tickets, min(num_to_pick, len(backlog_tickets)))
        
        selected_ids = []
        for t in selected:
            store.update_ticket_status(t['id'], "TODO")
            store.add_comment(t['id'], "Selected for development by PO")
            selected_ids.append(t['id'])
            
        return {"use_case_tickets": selected_ids, "messages": [AIMessage(content=f"PO Agent selected backlog tickets (mock): {', '.join(selected_ids)}")]}

    llm = get_llm().with_structured_output(POSelection)
    
    ticket_list_str = "\n".join([f"- ID: {t['id']}, Title: {t['title']}, Desc: {t.get('description', '')}" for t in backlog_tickets])

    messages = [
        ("system", PO_AGENT_PROMPT),
        ("human", f"Backlog Tickets:\n{ticket_list_str}")
    ]

    try:
        result = llm.invoke(messages)
        selected_ids = result.selected_ticket_ids if result and result.selected_ticket_ids else []
    except Exception as e:
        logger.error(f"PO Agent LLM selection failed: {e}")
        selected_ids = []
        
    actual_selected = []
    for t_id in selected_ids:
        if any(bt['id'] == t_id for bt in backlog_tickets):
            store.update_ticket_status(t_id, "TODO")
            store.add_comment(t_id, "Selected for development by PO")
            actual_selected.append(t_id)
        
    return {"use_case_tickets": actual_selected, "messages": [AIMessage(content=f"PO Agent selected backlog tickets via LLM: {', '.join(actual_selected)}")]}

def dev_lead_agent(state: AppState) -> dict:
    store = get_ticket_store()
    logger.info("--- Dev Lead Agent: Creating Dev Tasks ---")
    
    dev_tickets = state.get("dev_tickets", [])
    if dev_tickets:
        # Avoid recreating tickets if already populated
        return {}

    if not is_llm_configured():
        logger.warning("LLM provider not configured. Using mock Dev Lead logic.")
        devops_id = store.create_ticket(title="Scaffold App", description="Setup next.js/supabase", ticket_type="devops")
        fe_id = store.create_ticket(title="Implement UI", description="Implement UI for use cases", ticket_type="frontend")
        be_id = store.create_ticket(title="Implement API", description="Implement API for use cases", ticket_type="backend")
        
        dev_tickets = [
            {"id": devops_id, "type": "devops", "status": "TODO"},
            {"id": fe_id, "type": "frontend", "status": "TODO"},
            {"id": be_id, "type": "backend", "status": "TODO"}
        ]
        return {"dev_tickets": dev_tickets, "messages": [AIMessage(content=f"Dev Lead assigned tasks (mock): {devops_id}, {fe_id}, {be_id}")]}

    # Gather use case details
    uc_details = []
    for uc_id in state.get("use_case_tickets", []):
        ticket = store.get_ticket(uc_id)
        if ticket:
            uc_details.append(f"- {ticket['title']}: {ticket['description']}")
    
    uc_text = "\n".join(uc_details)
    
    llm = get_llm().with_structured_output(DevLeadExtraction)
        
    messages = [
        ("system", DEV_LEAD_AGENT_PROMPT),
        ("human", f"Use Cases:\n{uc_text}")
    ]
    
    result = llm.invoke(messages)
    new_dev_tickets = []
    created_task_ids = []
    
    for task in result.tasks:
        # Validate task type before creating
        task_type = task.type if task.type in ["frontend", "backend", "devops"] else "backend"
        task_id = store.create_ticket(title=task.title, description=task.description, ticket_type=task_type)
        new_dev_tickets.append({"id": task_id, "type": task_type, "status": "TODO"})
        created_task_ids.append(task_id)
        
    return {"dev_tickets": new_dev_tickets, "messages": [AIMessage(content=f"Dev Lead generated dev tasks via LLM: {', '.join(created_task_ids)}")]}

def devops_agent(state: AppState) -> dict:
    store = get_ticket_store()
    vc = get_version_control()
    logger.info("--- DevOps Agent: Scaffolding ---")
    
    dev_tickets = state.get("dev_tickets", [])
    updated_tickets = []
    
    for t in dev_tickets:
        if t["type"] == "devops" and t["status"] == "TODO":
            if is_llm_configured():
                # Read task details
                ticket = store.get_ticket(t['id'])
                task_desc = ticket.get("description", "") if ticket else ""
                
                from langgraph.prebuilt import create_react_agent
                from app.tools.file_system import get_file_tools
                from app.tools.github import create_branch_tool, commit_code_tool, create_pr_tool
                
                llm = get_llm()
                # Create tools isolated to this agent
                tools = get_file_tools("/tmp/workspace", restrict_destructive=False) + [
                    create_branch_tool, commit_code_tool, create_pr_tool
                ]
                
                # Create the subgraph
                agent = create_react_agent(llm, tools=tools, prompt=DEVOPS_AGENT_PROMPT)
                
                try:
                    logger.info("Executing DevOps Subgraph...")
                    agent.invoke({"messages": [("human", f"Execute this task: {t['id']}\n\nTask Description:\n{task_desc}")]})
                    # Agent completes loop. Update ticket.
                    store.update_ticket_status(t['id'], "DONE")
                    t["status"] = "DONE"
                    store.add_comment(t['id'], "DevOps Agent completed its task via Subgraph.")
                except Exception as e:
                    logger.error(f"DevOps Agent Subgraph failed: {e}")
            else:
                logger.warning("LLM provider not configured. Using mock DevOps logic.")
                files_to_commit = {
                    "package.json": '{\n  "name": "mock-app",\n  "dependencies": {\n    "next": "latest",\n    "react": "latest",\n    "react-dom": "latest",\n    "@supabase/supabase-js": "latest"\n  }\n}',
                    "next.config.js": "module.exports = {};",
                    "tailwind.config.ts": "module.exports = { content: ['./src/**/*.{js,ts,jsx,tsx}'] };",
                    "src/app/page.tsx": "export default function Home() { return <div>Mock App</div>; }",
                    "src/lib/supabase.ts": "import { createClient } from '@supabase/supabase-js';\nexport const supabase = createClient('mock_url', 'mock_key');"
                }

                branch = vc.create_branch(f"devops-{t['id']}")
                vc.commit_code(branch, "Initial scaffold", files_to_commit)
                pr = vc.create_pull_request("Scaffold PR", "Added scaffold", branch)
                store.update_ticket_status(t['id'], "DONE")
                t["status"] = "DONE"
                store.add_comment(t['id'], f"PR created: {pr}")
        updated_tickets.append(t)
        
    return {"dev_tickets": updated_tickets, "messages": [AIMessage(content="DevOps completed scaffolding.")]}

def developer_agent(state: AppState) -> dict:
    store = get_ticket_store()
    vc = get_version_control()
    logger.info("--- Developer Agent: Coding ---")
    
    dev_tickets = state.get("dev_tickets", [])
    updated_tickets = []
    
    for t in dev_tickets:
        if t["type"] in ["frontend", "backend"] and t["status"] == "TODO":
            if is_llm_configured():
                ticket = store.get_ticket(t['id'])
                task_desc = ticket.get("description", "") if ticket else ""
                
                from langgraph.prebuilt import create_react_agent
                from app.tools.file_system import get_file_tools
                from app.tools.github import create_branch_tool, commit_code_tool, create_pr_tool
                from app.config.prompts import DEVELOPER_AGENT_PROMPT
                
                llm = get_llm()
                # Create tools isolated to this agent (restrict destructive actions)
                tools = get_file_tools("/tmp/workspace", restrict_destructive=True) + [
                    create_branch_tool, commit_code_tool, create_pr_tool
                ]
                
                agent = create_react_agent(llm, tools=tools, prompt=DEVELOPER_AGENT_PROMPT)
                
                try:
                    logger.info(f"Executing Developer Subgraph for {t['type']}...")
                    agent.invoke({"messages": [("human", f"Execute this {t['type']} task: {t['id']}\n\nTask Description:\n{task_desc}")]})
                    
                    store.update_ticket_status(t['id'], "DONE")
                    t["status"] = "DONE"
                    store.add_comment(t['id'], "Developer Agent completed its task via Subgraph.")
                except Exception as e:
                    logger.error(f"Developer Agent Subgraph failed: {e}")
            else:
                logger.warning("LLM provider not configured. Using mock Developer logic.")
                branch = vc.create_branch(f"dev-{t['id']}")
                vc.commit_code(branch, "Implemented feature", {"code.ts": "// code"})
                pr = vc.create_pull_request(f"{t['type']} feature PR", "Implemented code", branch)
                store.update_ticket_status(t['id'], "DONE")
                t["status"] = "DONE"
                store.add_comment(t['id'], f"PR created: {pr}")
        updated_tickets.append(t)
        
    return {"dev_tickets": updated_tickets, "messages": [AIMessage(content="Devs completed tasks.")]}

def qa_agent(state: AppState) -> dict:
    logger.info("--- QA Agent: Reviewing ---")
    # Mock QA just merges all open PRs in theory
    # For now, just mark state as completed.
    return {"messages": [AIMessage(content="QA Agent approved and merged PRs.")]}

def human_input(state: AppState) -> dict:
    logger.info("--- Human Input Required ---")
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
