"""
Vercel serverless function: GitHub App installation callback.
Handles the OAuth callback when users install the app.
"""
import os
import sys
import asyncio
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.client import create_installation, get_installation

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
        
        installation_id_str = params.get("installation_id", [None])[0]
        setup_action = params.get("setup_action", [None])[0]
        
        if not installation_id_str:
            # Redirect to home if no installation_id
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
            
        try:
            installation_id = int(installation_id_str)
            
            # Create or update installation record in Supabase
            # Note: In a real app, we should verify the installation with GitHub API first
            # to get the owner details. For MVP, we'll placeholder the owner until first webhook.
            
            # We need to run async database calls in synchronous handler
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            existing = loop.run_until_complete(get_installation(installation_id))
            
            if not existing:
                loop.run_until_complete(create_installation(
                    github_installation_id=installation_id,
                    owner_login="pending_owner", # Will be updated by webhook
                    owner_type="User"
                ))
                
            loop.close()
            
        except Exception as e:
            print(f"Error handling installation: {e}")
            # Continue to config page anyway
        
        # Redirect to configuration page
        config_url = f"/config.html?installation_id={installation_id_str}"
        
        self.send_response(302)
        self.send_header("Location", config_url)
        self.end_headers()
