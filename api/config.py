"""
Vercel serverless function: Configuration API.
Handles saving user's Gemini/Groq API key and settings.
"""
import os
import sys
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import (
    get_installation, 
    update_installation_api_key, 
    update_installation_settings
)

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
        """Get installation settings."""
        # Parse query parameters
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        installation_id_str = params.get("installation_id", [None])[0]
        
        if not installation_id_str:
            self.send_response(400)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Missing installation_id"}).encode())
            return
            
        try:
            installation_id = int(installation_id_str)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            installation = loop.run_until_complete(get_installation(installation_id))
            loop.close()
            
            if not installation:
                self.send_response(404)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Installation not found"}).encode())
                return
                
            response = {
                "installation_id": installation_id,
                "owner": installation.get("owner_login", "unknown"),
                "enabled": installation.get("enabled", True),
                "has_api_key": bool(installation.get("api_key_encrypted")),
                "settings": installation.get("settings", {})
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_POST(self):
        """Update installation settings."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode("utf-8"))
            installation_id = int(data.get("installation_id"))
            api_key = data.get("api_key")
            settings = data.get("settings")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Update API key if provided
            if api_key:
                loop.run_until_complete(update_installation_api_key(installation_id, api_key))
            
            # Update settings if provided
            if settings:
                loop.run_until_complete(update_installation_settings(installation_id, settings))
                
            loop.close()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "updated"}).encode())
            
        except Exception as e:
            self.send_response(500)
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
