import logging
import requests
from typing import Dict, Any, Optional
from app.interfaces.ticket_store import ITicketStore

logger = logging.getLogger(__name__)

class LinearTicketStore(ITicketStore):
    def __init__(self, api_key: str, team_id: str):
        self.api_key = api_key
        self.team_id = team_id
        self.url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        self._states_cache = {}

    def _run_query(self, query: str, variables: dict) -> dict:
        response = requests.post(
            self.url,
            json={"query": query, "variables": variables},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def _get_state_id(self, target_type: str) -> Optional[str]:
        # target_type maps to Linear's internal workflow state types: "unstarted", "started", "completed", "canceled"
        if not self._states_cache:
            query = """
            query GetStates($teamId: String!) {
              team(id: $teamId) {
                states { nodes { id type } }
              }
            }
            """
            try:
                res = self._run_query(query, {"teamId": self.team_id})
                nodes = res.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
                for node in nodes:
                    # In case multiple states have the same type, keep the first one we see
                    if node["type"] not in self._states_cache:
                        self._states_cache[node["type"]] = node["id"]
            except Exception as e:
                logger.error(f"[LinearTicketStore] Failed to fetch team states: {e}")
        
        return self._states_cache.get(target_type)

    def create_ticket(self, title: str, description: str, ticket_type: str = "feature") -> str:
        query = """
        mutation IssueCreate($teamId: String!, $title: String!, $description: String) {
          issueCreate(input: {teamId: $teamId, title: $title, description: $description}) {
            issue { id identifier title }
          }
        }
        """
        # Linear doesn't have a native 'ticket type' without custom labels, so we'll prepend it to the description
        desc_with_type = f"**Task Type:** {ticket_type.upper()}\n\n{description}"
        variables = {
            "teamId": self.team_id,
            "title": title,
            "description": desc_with_type
        }
        try:
            res = self._run_query(query, variables)
            if "errors" in res:
                logger.error(f"[LinearTicketStore] GraphQL Error creating ticket: {res['errors']}")
                return ""
                
            issue = res.get("data", {}).get("issueCreate", {}).get("issue", {})
            issue_id = issue.get("id")
            logger.info(f"[LinearTicketStore] Created ticket {issue.get('identifier')} ({issue_id}): {title}")
            return issue_id
        except Exception as e:
            logger.error(f"[LinearTicketStore] Failed to create ticket: {e}")
            return ""

    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        # Map our internal statuses to Linear's state types
        type_mapping = {
            "TODO": "unstarted",
            "IN PROGRESS": "started",
            "DONE": "completed"
        }
        target_type = type_mapping.get(status.upper(), "unstarted")
        state_id = self._get_state_id(target_type)
        
        if not state_id:
            logger.error(f"[LinearTicketStore] Could not find Linear state ID mapping for status '{status}' (type: {target_type})")
            return

        query = """
        mutation IssueUpdate($id: String!, $stateId: String!) {
          issueUpdate(id: $id, input: {stateId: $stateId}) { success }
        }
        """
        try:
            res = self._run_query(query, {"id": ticket_id, "stateId": state_id})
            if "errors" in res:
                logger.error(f"[LinearTicketStore] GraphQL Error updating ticket: {res['errors']}")
            else:
                logger.info(f"[LinearTicketStore] Updated ticket {ticket_id} to status '{status}'")
        except Exception as e:
            logger.error(f"[LinearTicketStore] Failed to update ticket status: {e}")

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        query = """
        query GetIssue($id: String!) {
          issue(id: $id) { id title description state { name type } }
        }
        """
        try:
            res = self._run_query(query, {"id": ticket_id})
            issue = res.get("data", {}).get("issue")
            if issue:
                # Map Linear's state type back to our expected status format
                state_type = issue.get("state", {}).get("type")
                if state_type == "completed":
                    issue["status"] = "DONE"
                elif state_type == "started":
                    issue["status"] = "IN PROGRESS"
                else:
                    issue["status"] = "TODO"
                    
                # Standardize 'type' field to prevent KeyError in our workflow checks
                issue["type"] = "feature" # Fallback if we can't parse it
                
            return issue
        except Exception as e:
            logger.error(f"[LinearTicketStore] Failed to get ticket: {e}")
            return None

    def add_comment(self, ticket_id: str, comment: str) -> None:
        query = """
        mutation CommentCreate($issueId: String!, $body: String!) {
          commentCreate(input: {issueId: $issueId, body: $body}) { success }
        }
        """
        try:
            res = self._run_query(query, {"issueId": ticket_id, "body": comment})
            if "errors" in res:
                logger.error(f"[LinearTicketStore] GraphQL Error adding comment: {res['errors']}")
            else:
                logger.info(f"[LinearTicketStore] Added comment to {ticket_id}")
        except Exception as e:
            logger.error(f"[LinearTicketStore] Failed to add comment: {e}")
