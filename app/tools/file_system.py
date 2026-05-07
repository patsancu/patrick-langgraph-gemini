import os
from langchain_community.agent_toolkits.file_management.toolkit import FileManagementToolkit

def get_file_tools(workspace_path: str, restrict_destructive: bool = True):
    """
    Returns a securely sandboxed set of file tools.
    """
    os.makedirs(workspace_path, exist_ok=True)
    selected_tools = ["read_file", "write_file", "list_directory", "file_search"]
    
    if not restrict_destructive:
        selected_tools.extend(["copy_file", "move_file", "file_delete"])
        
    toolkit = FileManagementToolkit(
        root_dir=workspace_path,
        selected_tools=selected_tools
    )
    return toolkit.get_tools()