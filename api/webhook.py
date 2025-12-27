"""
Vercel serverless function: GitHub webhook handler.
Receives pull_request events, runs AI code review, and posts comments.
"""
import os
import sys
import json
import hmac
import hashlib
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature."""
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


def get_github_client(installation_id: int):
    """Get authenticated GitHub client for an installation."""
    import jwt
    import time
    import httpx
    
    app_id = os.environ.get("GITHUB_APP_ID")
    private_key = os.environ.get("GITHUB_PRIVATE_KEY", "").replace("\\n", "\n")
    
    if not app_id or not private_key:
        raise Exception("Missing GITHUB_APP_ID or GITHUB_PRIVATE_KEY")
    
    # Create JWT
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": app_id
    }
    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
    
    # Get installation access token
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }
    
    with httpx.Client() as client:
        resp = client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers=headers
        )
        resp.raise_for_status()
        token = resp.json()["token"]
    
    return token


def get_pr_files(token: str, owner: str, repo: str, pr_number: int) -> list:
    """Get files changed in a PR."""
    import httpx
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    with httpx.Client() as client:
        resp = client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files",
            headers=headers
        )
        resp.raise_for_status()
        return resp.json()


def get_file_content(token: str, owner: str, repo: str, path: str, ref: str) -> str:
    """Get file content from GitHub."""
    import httpx
    import base64
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    with httpx.Client() as client:
        resp = client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}",
            headers=headers
        )
        if resp.status_code != 200:
            return ""
        
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return ""


def post_review_comment(token: str, owner: str, repo: str, pr_number: int, body: str):
    """Post a review comment on the PR."""
    import httpx
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    with httpx.Client() as client:
        resp = client.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers=headers,
            json={"body": body}
        )
        resp.raise_for_status()


def run_ai_review(code: str, file_path: str) -> str:
    """Run AI review on code and return markdown comment."""
    from agents.llm_client import get_llm_client
    
    client = get_llm_client()
    
    prompt = f"""You are an expert code reviewer. Review this code for:
1. Security issues (hardcoded secrets, vulnerabilities)
2. Bug potential (logic errors, edge cases)
3. Best practices violations

Code file: {file_path}
```
{code[:3000]}
```

If issues found, list them in this format:
### 🔍 Code Review - {file_path}

**Issues Found:**
- 🔴 **Critical**: [description]
- 🟡 **Warning**: [description]
- 💡 **Suggestion**: [description]

If no issues, say "✅ No significant issues found."

Be concise. Focus on real problems, not style nitpicks."""

    try:
        response = client.generate(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Review failed for {file_path}: {str(e)[:100]}"


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_POST(self):
        """Handle POST requests (GitHub webhooks)."""
        
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        # Verify signature
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(body, signature):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid signature"}).encode())
            return
        
        # Parse payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return
        
        # Check event type
        event_type = self.headers.get("X-GitHub-Event", "")
        if event_type != "pull_request":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Event ignored"}).encode())
            return
        
        # Check action
        action = payload.get("action", "")
        if action not in ["opened", "synchronize", "reopened"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Action ignored"}).encode())
            return
        
        # Extract PR info
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        installation = payload.get("installation", {})
        
        pr_number = pr.get("number")
        head_sha = pr.get("head", {}).get("sha")
        owner = repo.get("owner", {}).get("login")
        repo_name = repo.get("name")
        installation_id = installation.get("id")
        
        if not all([pr_number, owner, repo_name, installation_id]):
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing PR data"}).encode())
            return
        
        try:
            # Get access token
            token = get_github_client(installation_id)
            
            # Get PR files
            files = get_pr_files(token, owner, repo_name, pr_number)
            
            # Filter to reviewable files
            reviewable_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb"]
            reviewable_files = [
                f for f in files 
                if any(f.get("filename", "").endswith(ext) for ext in reviewable_extensions)
                and f.get("status") != "removed"
            ]
            
            if not reviewable_files:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"message": "No reviewable files"}).encode())
                return
            
            # Review each file
            reviews = []
            for file_info in reviewable_files[:5]:  # Limit to 5 files
                filename = file_info.get("filename", "")
                content = get_file_content(token, owner, repo_name, filename, head_sha)
                
                if content:
                    review = run_ai_review(content, filename)
                    reviews.append(review)
            
            # Post combined review
            if reviews:
                comment = "## 🤖 CodeLens AI Review\n\n" + "\n\n---\n\n".join(reviews)
                post_review_comment(token, owner, repo_name, pr_number, comment)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "reviewed",
                "files_reviewed": len(reviewable_files)
            }).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "healthy",
            "service": "AI Code Review Webhook"
        }).encode())
