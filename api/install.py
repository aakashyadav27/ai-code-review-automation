"""
Vercel serverless function: GitHub App installation callback.
Handles the OAuth callback when users install the app.
"""
import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add parent directory to path for imports
import sys
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
        
        installation_id = params.get("installation_id", [None])[0]
        setup_action = params.get("setup_action", [""])[0]
        
        if not installation_id:
            # Redirect to home if no installation_id
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        
        # Check if installation already exists
        try:
            installation_id_int = int(installation_id)
            existing = asyncio.run(get_installation(installation_id_int))
            
            if not existing:
                # For new installations, we'll create a placeholder
                # The actual owner info comes from the webhook, but we can
                # create a basic record here
                asyncio.run(create_installation(
                    github_installation_id=installation_id_int,
                    owner_login="pending",  # Will be updated by webhook
                    owner_type="User"
                ))
            
            # Redirect to configuration page
            config_url = f"/config.html?installation_id={installation_id}"
            
            self.send_response(302)
            self.send_header("Location", config_url)
            self.end_headers()
            
        except Exception as e:
            # Show error page
            self.send_response(500)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Installation Error</title></head>
            <body>
                <h1>Installation Error</h1>
                <p>There was an error setting up your installation: {str(e)}</p>
                <p>Please try again or contact support.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
