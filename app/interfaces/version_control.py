from abc import ABC, abstractmethod

class IVersionControl(ABC):
    @abstractmethod
    def create_branch(self, branch_name: str) -> str:
        pass

    @abstractmethod
    def commit_code(self, branch_name: str, message: str, files: dict) -> None:
        pass

    @abstractmethod
    def create_pull_request(self, title: str, description: str, branch_name: str) -> str:
        pass

    @abstractmethod
    def merge_pull_request(self, pr_id: str) -> None:
        pass

class MockVersionControl(IVersionControl):
    def create_branch(self, branch_name: str) -> str:
        print(f"[MockVersionControl] Created branch: {branch_name}")
        return branch_name

    def commit_code(self, branch_name: str, message: str, files: dict) -> None:
        print(f"[MockVersionControl] Committed to {branch_name} | Message: {message} | Files: {list(files.keys())}")

    def create_pull_request(self, title: str, description: str, branch_name: str) -> str:
        pr_id = f"PR-{branch_name}"
        print(f"[MockVersionControl] Created PR {pr_id}: {title} from branch {branch_name}")
        return pr_id

    def merge_pull_request(self, pr_id: str) -> None:
        print(f"[MockVersionControl] Merged PR {pr_id}")
