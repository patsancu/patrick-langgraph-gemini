import logging
from github import Github, InputGitTreeElement
from app.interfaces.version_control import IVersionControl

logger = logging.getLogger(__name__)

class GithubVersionControl(IVersionControl):
    def __init__(self, token: str, repo_name: str):
        self.gh = Github(token)
        self.repo = self.gh.get_repo(repo_name)
        
    def create_branch(self, branch_name: str) -> str:
        try:
            source_branch = self.repo.default_branch
            source_ref = self.repo.get_git_ref(f"heads/{source_branch}")
            self.repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_ref.object.sha)
            logger.info(f"[GithubVersionControl] Created branch {branch_name} from {source_branch}")
        except Exception as e:
            logger.error(f"[GithubVersionControl] Failed to create branch {branch_name}: {e}")
        return branch_name

    def commit_code(self, branch_name: str, message: str, files: dict) -> None:
        try:
            ref = self.repo.get_git_ref(f"heads/{branch_name}")
            base_tree = self.repo.get_git_tree(ref.object.sha)
            
            tree_elements = []
            for file_path, content in files.items():
                element = InputGitTreeElement(
                    path=file_path,
                    mode="100644",
                    type="blob",
                    content=content
                )
                tree_elements.append(element)
                
            tree = self.repo.create_git_tree(tree_elements, base_tree)
            parent = self.repo.get_git_commit(ref.object.sha)
            commit = self.repo.create_git_commit(message, tree, [parent])
            
            ref.edit(commit.sha)
            logger.info(f"[GithubVersionControl] Committed to {branch_name}: {message}")
        except Exception as e:
            logger.error(f"[GithubVersionControl] Failed to commit to {branch_name}: {e}")

    def create_pull_request(self, title: str, description: str, branch_name: str) -> str:
        try:
            base = self.repo.default_branch
            pr = self.repo.create_pull(
                title=title,
                body=description,
                head=branch_name,
                base=base
            )
            logger.info(f"[GithubVersionControl] Created PR #{pr.number}: {title}")
            return str(pr.html_url)
        except Exception as e:
            logger.error(f"[GithubVersionControl] Failed to create PR: {e}")
            return ""

    def merge_pull_request(self, pr_id: str) -> None:
        try:
            # Handle if pr_id is passed as a URL string or an ID
            pr_number = int(pr_id.split("/")[-1]) if "http" in pr_id else int(pr_id)
            pr = self.repo.get_pull(pr_number)
            pr.merge()
            logger.info(f"[GithubVersionControl] Merged PR #{pr_number}")
        except Exception as e:
            logger.error(f"[GithubVersionControl] Failed to merge PR {pr_id}: {e}")
