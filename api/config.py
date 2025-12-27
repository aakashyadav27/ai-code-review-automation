"""
Vercel serverless function: Configuration API.
Handles saving user's Gemini API key and settings.
"""
import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs


class handler(BaseHTTPRequestHandler):
    """Handle configuration API requests."""
    
    def _set_cors_headers(self):
        """Set CORS headers for browser requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Get installation settings or health check."""
        # Parse query parameters
        query = self.path.split("?")[1] if "?" in self.path else ""
        params = parse_qs(query)
        
        installation_id = params.get("installation_id", [None])[0]
        
        if not installation_id:
            # Health check
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "AI Code Review Config API"
            }).encode())
            return
        
        # Return placeholder config (database not connected yet)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({
            "installation_id": installation_id,
            "owner": "pending",
            "enabled": True,
            "has_api_key": False,
            "settings": {
                "review_style": True,
                "review_security": True,
                "review_performance": True,
                "review_logic": True
            }
        }).encode())
    
    def do_POST(self):
        """Update installation settings."""
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return
        
        # Return success (database not connected yet)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"status": "updated"}).encode())
