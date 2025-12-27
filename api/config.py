"""
Vercel serverless function: Configuration API.
Handles saving user's Gemini API key and settings.
"""
import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import (
    get_installation,
    update_installation_api_key,
    update_installation_settings,
    get_installation_api_key
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
        """
        Get installation settings.
        Query param: installation_id
        """
        # Parse query parameters
        query = self.path.split("?")[1] if "?" in self.path else ""
        params = parse_qs(query)
        
        installation_id = params.get("installation_id", [None])[0]
        
        if not installation_id:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "installation_id required"}).encode())
            return
        
        try:
            installation = asyncio.run(get_installation(int(installation_id)))
            
            if not installation:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Installation not found"}).encode())
                return
            
            # Check if API key is configured (don't return the actual key)
            has_api_key = bool(installation.get("api_key_encrypted"))
            
            response = {
                "installation_id": installation["github_installation_id"],
                "owner": installation["owner_login"],
                "enabled": installation["enabled"],
                "has_api_key": has_api_key,
                "settings": installation.get("settings", {})
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_POST(self):
        """
        Update installation settings.
        Body: {installation_id, api_key?, settings?}
        """
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
        
        installation_id = data.get("installation_id")
        
        if not installation_id:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "installation_id required"}).encode())
            return
        
        try:
            installation_id_int = int(installation_id)
            
            # Update API key if provided
            if "api_key" in data:
                api_key = data["api_key"]
                if api_key:
                    asyncio.run(update_installation_api_key(
                        installation_id_int,
                        api_key
                    ))
            
            # Update settings if provided
            if "settings" in data:
                asyncio.run(update_installation_settings(
                    installation_id_int,
                    data["settings"]
                ))
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "updated"}).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
