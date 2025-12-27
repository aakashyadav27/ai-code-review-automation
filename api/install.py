"""
Vercel serverless function: GitHub App installation callback.
Handles the OAuth callback when users install the app.
"""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


class handler(BaseHTTPRequestHandler):
    """Handle GitHub App installation callbacks."""
    
    def do_GET(self):
        """
        Handle GET request from GitHub after app installation.
        GitHub redirects here with installation_id and setup_action params.
        """
        
        # Parse query parameters
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        installation_id = params.get("installation_id", [None])[0]
        
        if not installation_id:
            # Redirect to home if no installation_id
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        
        # Redirect to configuration page
        config_url = f"/config.html?installation_id={installation_id}"
        
        self.send_response(302)
        self.send_header("Location", config_url)
        self.end_headers()
