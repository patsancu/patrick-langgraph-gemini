from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.dependencies import get_version_control

class CreateBranchInput(BaseModel):
    branch_name: str = Field(description="The name of the branch to create")

@tool("create_branch", args_schema=CreateBranchInput)
def create_branch_tool(branch_name: str) -> str:
    """Create a new branch in the version control system."""
    vc = get_version_control()
    return vc.create_branch(branch_name)

class CommitCodeInput(BaseModel):
    branch_name: str = Field(description="The name of the branch to commit to")
    message: str = Field(description="The commit message")
    files_changed: list[str] = Field(description="List of file paths that were changed")

@tool("commit_code", args_schema=CommitCodeInput)
def commit_code_tool(branch_name: str, message: str, files_changed: list[str]) -> str:
    """Commit the modified files to the branch."""
    vc = get_version_control()
    
    files_dict = {}
    import os
    workspace = "/tmp/workspace"
    for f in files_changed:
        file_path = os.path.join(workspace, f)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file_obj:
                files_dict[f] = file_obj.read()
                
    vc.commit_code(branch_name, message, files_dict)
    return f"Committed {len(files_dict)} files to {branch_name}"

class CreatePRInput(BaseModel):
    title: str = Field(description="The title of the pull request")
    description: str = Field(description="The description of the pull request")
    branch_name: str = Field(description="The branch to create the PR from")

@tool("create_pull_request", args_schema=CreatePRInput)
def create_pr_tool(title: str, description: str, branch_name: str) -> str:
    """Create a pull request from the specified branch."""
    vc = get_version_control()
    return vc.create_pull_request(title, description, branch_name)