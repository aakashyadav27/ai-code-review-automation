"""
GitHub webhook handler - validates and parses incoming webhooks.
"""
import os
import hmac
import hashlib
from typing import Optional
from dataclasses import dataclass


@dataclass
class WebhookPayload:
    """Parsed webhook payload for pull_request events."""
    action: str
    pr_number: int
    repo_full_name: str
    repo_owner: str
    repo_name: str
    installation_id: int
    sender: str
    head_sha: str
    base_ref: str
    head_ref: str
    pr_title: str
    pr_body: str


def verify_webhook_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str = None
) -> bool:
    """
    Verify GitHub webhook signature.
    
    Args:
        payload_body: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value
        secret: Webhook secret (defaults to GITHUB_WEBHOOK_SECRET env var)
    
    Returns:
        True if signature is valid, False otherwise
    """
    secret = secret or os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    
    if not signature_header:
        return False
    
    # Extract hash from header (format: sha256=<hash>)
    if not signature_header.startswith("sha256="):
        return False
    
    expected_signature = signature_header[7:]
    
    # Calculate expected signature
    computed_signature = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare using constant-time comparison
    return hmac.compare_digest(computed_signature, expected_signature)


def parse_pull_request_event(payload: dict) -> Optional[WebhookPayload]:
    """
    Parse a pull_request webhook payload.
    
    Args:
        payload: Parsed JSON webhook body
        
    Returns:
        WebhookPayload if valid pull_request event, None otherwise
    """
    # Check if this is a pull_request event with relevant action
    action = payload.get("action")
    if action not in ("opened", "synchronize", "reopened"):
        return None
    
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})
    
    if not pr or not repo:
        return None
    
    repo_full_name = repo.get("full_name", "")
    repo_parts = repo_full_name.split("/")
    
    return WebhookPayload(
        action=action,
        pr_number=pr.get("number"),
        repo_full_name=repo_full_name,
        repo_owner=repo_parts[0] if len(repo_parts) == 2 else "",
        repo_name=repo_parts[1] if len(repo_parts) == 2 else "",
        installation_id=installation.get("id"),
        sender=payload.get("sender", {}).get("login", ""),
        head_sha=pr.get("head", {}).get("sha", ""),
        base_ref=pr.get("base", {}).get("ref", ""),
        head_ref=pr.get("head", {}).get("ref", ""),
        pr_title=pr.get("title", ""),
        pr_body=pr.get("body", "") or ""
    )


def is_reviewable_file(filename: str) -> bool:
    """
    Check if a file should be reviewed.
    
    Args:
        filename: Path of the file
        
    Returns:
        True if file should be reviewed
    """
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".go", ".rs", ".java", ".rb", ".php",
        ".c", ".cpp", ".cs", ".swift", ".kt"
    }
    
    # Files/patterns to skip
    SKIP_PATTERNS = {
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "Pipfile.lock",
        ".min.js",
        ".min.css",
        "vendor/",
        "node_modules/",
        "__pycache__/",
        ".git/",
    }
    
    # Check if file matches skip patterns
    for pattern in SKIP_PATTERNS:
        if pattern in filename:
            return False
    
    # Check if extension is supported
    for ext in SUPPORTED_EXTENSIONS:
        if filename.endswith(ext):
            return True
    
    return False
