"""
GitHub API client for App authentication and PR operations.
"""
import os
import time
import jwt
import httpx
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class PullRequestFile:
    """Represents a file changed in a pull request."""
    filename: str
    status: str  # added, removed, modified, renamed
    additions: int
    deletions: int
    patch: Optional[str]  # Diff content
    contents_url: str


@dataclass 
class PullRequest:
    """Represents a GitHub pull request."""
    number: int
    title: str
    body: str
    head_sha: str
    base_ref: str
    head_ref: str
    repo_full_name: str
    author: str


class GitHubAppClient:
    """
    GitHub App client for authenticating and interacting with GitHub API.
    Uses App authentication to act on behalf of installations.
    """
    
    def __init__(
        self,
        app_id: str = None,
        private_key: str = None,
        installation_id: int = None
    ):
        """
        Initialize GitHub App client.
        
        Args:
            app_id: GitHub App ID
            private_key: GitHub App private key (PEM format)
            installation_id: Installation ID to authenticate as
        """
        self.app_id = app_id or os.environ.get("GITHUB_APP_ID")
        self.private_key = private_key or os.environ.get("GITHUB_PRIVATE_KEY")
        self.installation_id = installation_id
        self._installation_token = None
        self._token_expires_at = 0
        self.base_url = "https://api.github.com"
    
    def _generate_jwt(self) -> str:
        """Generate a JWT for App authentication."""
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 60 seconds ago
            "exp": now + (10 * 60),  # Expires in 10 minutes
            "iss": self.app_id
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")
    
    async def _get_installation_token(self) -> str:
        """Get or refresh installation access token."""
        now = time.time()
        
        # Return cached token if still valid
        if self._installation_token and now < self._token_expires_at - 60:
            return self._installation_token
        
        # Get new installation token
        jwt_token = self._generate_jwt()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/app/installations/{self.installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            response.raise_for_status()
            data = response.json()
            
        self._installation_token = data["token"]
        # Token expires in 1 hour, but we refresh 1 minute early
        self._token_expires_at = now + 3600
        
        return self._installation_token
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> dict:
        """Make an authenticated request to GitHub API."""
        token = await self._get_installation_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {}
    
    async def get_pull_request(self, repo: str, pr_number: int) -> PullRequest:
        """
        Get pull request details.
        
        Args:
            repo: Repository full name (owner/repo)
            pr_number: Pull request number
        """
        data = await self._request("GET", f"/repos/{repo}/pulls/{pr_number}")
        
        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data.get("body", ""),
            head_sha=data["head"]["sha"],
            base_ref=data["base"]["ref"],
            head_ref=data["head"]["ref"],
            repo_full_name=repo,
            author=data["user"]["login"]
        )
    
    async def get_pull_request_files(
        self, 
        repo: str, 
        pr_number: int
    ) -> List[PullRequestFile]:
        """
        Get files changed in a pull request.
        
        Args:
            repo: Repository full name (owner/repo)
            pr_number: Pull request number
        """
        data = await self._request(
            "GET", 
            f"/repos/{repo}/pulls/{pr_number}/files",
            params={"per_page": 100}
        )
        
        files = []
        for file_data in data:
            files.append(PullRequestFile(
                filename=file_data["filename"],
                status=file_data["status"],
                additions=file_data["additions"],
                deletions=file_data["deletions"],
                patch=file_data.get("patch"),
                contents_url=file_data["contents_url"]
            ))
        
        return files
    
    async def get_file_content(self, repo: str, path: str, ref: str) -> str:
        """
        Get file content from repository.
        
        Args:
            repo: Repository full name (owner/repo)
            path: File path in repository
            ref: Git reference (branch, commit SHA)
        """
        import base64
        
        data = await self._request(
            "GET",
            f"/repos/{repo}/contents/{path}",
            params={"ref": ref}
        )
        
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
        return data.get("content", "")
    
    async def create_pull_request_review(
        self,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: List[dict] = None
    ) -> dict:
        """
        Create a review on a pull request.
        
        Args:
            repo: Repository full name (owner/repo)
            pr_number: Pull request number
            body: Review body/summary
            event: Review event (COMMENT, APPROVE, REQUEST_CHANGES)
            comments: List of inline comments
        """
        payload = {
            "body": body,
            "event": event
        }
        
        if comments:
            payload["comments"] = comments
        
        return await self._request(
            "POST",
            f"/repos/{repo}/pulls/{pr_number}/reviews",
            json=payload
        )
    
    async def create_issue_comment(
        self,
        repo: str,
        issue_number: int,
        body: str
    ) -> dict:
        """
        Create a comment on an issue or pull request.
        
        Args:
            repo: Repository full name (owner/repo)
            issue_number: Issue/PR number
            body: Comment body
        """
        return await self._request(
            "POST",
            f"/repos/{repo}/issues/{issue_number}/comments",
            json={"body": body}
        )
