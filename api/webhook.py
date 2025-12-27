"""
Vercel serverless function: GitHub webhook handler.
Receives pull_request events and triggers AI code review.
"""
import os
import json
import time
import asyncio
from http.server import BaseHTTPRequestHandler

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from github.webhook_handler import (
    verify_webhook_signature,
    parse_pull_request_event,
    is_reviewable_file
)
from github.client import GitHubAppClient
from agents import StyleAgent, SecurityAgent, PerformanceAgent, LogicAgent
from db.client import (
    get_installation,
    get_installation_api_key,
    create_review,
    update_review
)


def format_review_comment(all_issues: list, file_count: int, duration_ms: int) -> str:
    """Format all issues into a GitHub comment."""
    
    if not all_issues:
        return """## 🤖 AI Code Review

✅ **No issues found!** Your code looks good.

---
<sub>Reviewed {files} file(s) in {time:.1f}s</sub>
""".format(files=file_count, time=duration_ms/1000)
    
    # Group issues by category
    by_category = {"style": [], "security": [], "performance": [], "logic": []}
    for issue in all_issues:
        by_category[issue.category].append(issue)
    
    # Build comment
    lines = ["## 🤖 AI Code Review\n"]
    
    # Summary
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠", 
        "medium": "🟡",
        "low": "🔵",
        "info": "⚪"
    }
    
    total = len(all_issues)
    critical = sum(1 for i in all_issues if i.severity.value == "critical")
    high = sum(1 for i in all_issues if i.severity.value == "high")
    
    if critical > 0:
        lines.append(f"⚠️ **Found {total} issue(s)** including **{critical} critical**\n")
    elif high > 0:
        lines.append(f"⚠️ **Found {total} issue(s)** including **{high} high severity**\n")
    else:
        lines.append(f"📋 **Found {total} issue(s)** to review\n")
    
    # Issues by category
    category_info = {
        "security": ("🔒 Security", "security_issues"),
        "style": ("🎨 Style", "style_issues"),
        "performance": ("⚡ Performance", "performance_issues"),
        "logic": ("🧠 Logic", "logic_issues")
    }
    
    for category, (title, _) in category_info.items():
        issues = by_category[category]
        if not issues:
            continue
            
        lines.append(f"\n### {title} ({len(issues)})\n")
        
        for issue in issues:
            emoji = severity_emoji.get(issue.severity.value, "⚪")
            lines.append(f"\n{emoji} **{issue.title}**")
            lines.append(f"- 📁 `{issue.file_path}` (line {issue.line_start})")
            lines.append(f"- {issue.description}")
            if issue.suggestion:
                lines.append(f"- 💡 **Suggestion:** {issue.suggestion}")
    
    # Footer
    lines.append("\n---")
    lines.append(f"<sub>Reviewed {file_count} file(s) in {duration_ms/1000:.1f}s</sub>")
    
    return "\n".join(lines)


async def process_review(payload):
    """Process a pull request review."""
    start_time = time.time()
    
    # Get installation and API key
    installation = await get_installation(payload.installation_id)
    if not installation:
        return {"error": "Installation not found"}
    
    if not installation.get("enabled"):
        return {"message": "Review disabled for this installation"}
    
    api_key = await get_installation_api_key(payload.installation_id)
    if not api_key:
        return {"error": "No API key configured. Please configure your Gemini API key."}
    
    # Initialize GitHub client
    github_client = GitHubAppClient(installation_id=payload.installation_id)
    
    # Create review record
    review_record = await create_review(
        installation_id=installation["id"],
        repo_full_name=payload.repo_full_name,
        pr_number=payload.pr_number,
        pr_title=payload.pr_title,
        commit_sha=payload.head_sha
    )
    
    try:
        # Get PR files
        files = await github_client.get_pull_request_files(
            payload.repo_full_name,
            payload.pr_number
        )
        
        # Filter reviewable files
        reviewable_files = [f for f in files if is_reviewable_file(f.filename)]
        
        if not reviewable_files:
            await github_client.create_issue_comment(
                payload.repo_full_name,
                payload.pr_number,
                "## 🤖 AI Code Review\n\n✅ No reviewable code files in this PR."
            )
            return {"message": "No reviewable files"}
        
        # Get settings
        settings = installation.get("settings", {})
        
        # Initialize enabled agents
        agents = []
        if settings.get("review_style", True):
            agents.append(StyleAgent(api_key))
        if settings.get("review_security", True):
            agents.append(SecurityAgent(api_key))
        if settings.get("review_performance", True):
            agents.append(PerformanceAgent(api_key))
        if settings.get("review_logic", True):
            agents.append(LogicAgent(api_key))
        
        # Get file contents and review
        all_issues = []
        files_reviewed = 0
        
        for file_info in reviewable_files[:10]:  # Limit to 10 files per review
            try:
                content = await github_client.get_file_content(
                    payload.repo_full_name,
                    file_info.filename,
                    payload.head_sha
                )
                
                # Run all agents on this file
                for agent in agents:
                    review = await agent.review_code(
                        code=content,
                        file_path=file_info.filename,
                        context=f"PR: {payload.pr_title}\n{payload.pr_body}"
                    )
                    all_issues.extend(review.issues)
                
                files_reviewed += 1
                
            except Exception as e:
                # Skip files that can't be fetched
                continue
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Format and post comment
        comment = format_review_comment(all_issues, files_reviewed, duration_ms)
        await github_client.create_issue_comment(
            payload.repo_full_name,
            payload.pr_number,
            comment
        )
        
        # Update review record
        issues_by_type = {
            "style": sum(1 for i in all_issues if i.category == "style"),
            "security": sum(1 for i in all_issues if i.category == "security"),
            "performance": sum(1 for i in all_issues if i.category == "performance"),
            "logic": sum(1 for i in all_issues if i.category == "logic")
        }
        
        await update_review(
            review_id=review_record["id"],
            files_reviewed=files_reviewed,
            issues_found=len(all_issues),
            issues_by_type=issues_by_type,
            review_duration_ms=duration_ms,
            status="completed"
        )
        
        return {
            "status": "completed",
            "files_reviewed": files_reviewed,
            "issues_found": len(all_issues)
        }
        
    except Exception as e:
        # Update review as failed
        await update_review(
            review_id=review_record["id"],
            status="failed",
            error_message=str(e)
        )
        raise


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_POST(self):
        """Handle POST requests (GitHub webhooks)."""
        
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        # Verify signature
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_webhook_signature(body, signature):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid signature"}).encode())
            return
        
        # Parse payload
        try:
            payload_dict = json.loads(body.decode("utf-8"))
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
        
        # Parse pull request event
        payload = parse_pull_request_event(payload_dict)
        if not payload:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Action ignored"}).encode())
            return
        
        # Process review asynchronously
        try:
            result = asyncio.run(process_review(payload))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
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
