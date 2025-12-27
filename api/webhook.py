"""
Vercel serverless function: GitHub webhook handler.
Receives pull_request events and triggers AI code review.
"""
import os
import json
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_POST(self):
        """Handle POST requests (GitHub webhooks)."""
        from github.webhook_handler import (
            verify_webhook_signature,
            parse_pull_request_event,
        )
        
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
        
        # Return success - actual review processing would be async
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "received",
            "pr_number": payload.pr_number,
            "repo": payload.repo_full_name
        }).encode())
    
    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "healthy",
            "service": "AI Code Review Webhook"
        }).encode())
