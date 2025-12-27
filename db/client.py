"""
Supabase database client with encryption helpers for storing API keys securely.
"""
import os
from typing import Optional
from cryptography.fernet import Fernet
from supabase import create_client, Client

# Initialize Supabase client
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _supabase_client = create_client(url, key)
    return _supabase_client


def get_fernet() -> Fernet:
    """Get Fernet encryption instance."""
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY must be set")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    fernet = get_fernet()
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from storage."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_key.encode()).decode()


# ============= Installation Operations =============

async def get_installation(github_installation_id: int) -> Optional[dict]:
    """Get installation by GitHub installation ID."""
    supabase = get_supabase()
    result = supabase.table("installations").select("*").eq(
        "github_installation_id", github_installation_id
    ).execute()
    return result.data[0] if result.data else None


async def create_installation(
    github_installation_id: int,
    owner_login: str,
    owner_type: str = "User"
) -> dict:
    """Create a new installation record."""
    supabase = get_supabase()
    result = supabase.table("installations").insert({
        "github_installation_id": github_installation_id,
        "owner_login": owner_login,
        "owner_type": owner_type,
    }).execute()
    return result.data[0]


async def update_installation_api_key(
    github_installation_id: int,
    api_key: str
) -> dict:
    """Update the API key for an installation (encrypts before storing)."""
    supabase = get_supabase()
    encrypted = encrypt_api_key(api_key)
    result = supabase.table("installations").update({
        "api_key_encrypted": encrypted
    }).eq("github_installation_id", github_installation_id).execute()
    return result.data[0] if result.data else None


async def get_installation_api_key(github_installation_id: int) -> Optional[str]:
    """Get and decrypt the API key for an installation."""
    installation = await get_installation(github_installation_id)
    if installation and installation.get("api_key_encrypted"):
        return decrypt_api_key(installation["api_key_encrypted"])
    return None


async def update_installation_settings(
    github_installation_id: int,
    settings: dict
) -> dict:
    """Update settings for an installation."""
    supabase = get_supabase()
    result = supabase.table("installations").update({
        "settings": settings
    }).eq("github_installation_id", github_installation_id).execute()
    return result.data[0] if result.data else None


# ============= Review Operations =============

async def create_review(
    installation_id: str,
    repo_full_name: str,
    pr_number: int,
    pr_title: str = None,
    commit_sha: str = None
) -> dict:
    """Create a new review record."""
    supabase = get_supabase()
    result = supabase.table("reviews").insert({
        "installation_id": installation_id,
        "repo_full_name": repo_full_name,
        "pr_number": pr_number,
        "pr_title": pr_title,
        "commit_sha": commit_sha,
        "status": "pending"
    }).execute()
    return result.data[0]


async def update_review(
    review_id: str,
    files_reviewed: int = None,
    issues_found: int = None,
    issues_by_type: dict = None,
    review_duration_ms: int = None,
    status: str = None,
    error_message: str = None
) -> dict:
    """Update a review record with results."""
    supabase = get_supabase()
    update_data = {}
    if files_reviewed is not None:
        update_data["files_reviewed"] = files_reviewed
    if issues_found is not None:
        update_data["issues_found"] = issues_found
    if issues_by_type is not None:
        update_data["issues_by_type"] = issues_by_type
    if review_duration_ms is not None:
        update_data["review_duration_ms"] = review_duration_ms
    if status is not None:
        update_data["status"] = status
    if error_message is not None:
        update_data["error_message"] = error_message
    
    result = supabase.table("reviews").update(update_data).eq("id", review_id).execute()
    return result.data[0] if result.data else None


async def get_review_stats(installation_id: str, days: int = 30) -> dict:
    """Get review statistics for an installation."""
    supabase = get_supabase()
    # Note: For complex aggregations, you might want to use a Supabase function
    result = supabase.table("reviews").select("*").eq(
        "installation_id", installation_id
    ).gte(
        "created_at", f"now() - interval '{days} days'"
    ).execute()
    
    reviews = result.data or []
    total_issues = sum(r.get("issues_found", 0) for r in reviews)
    
    return {
        "total_reviews": len(reviews),
        "total_issues_found": total_issues,
        "avg_issues_per_review": total_issues / len(reviews) if reviews else 0
    }
