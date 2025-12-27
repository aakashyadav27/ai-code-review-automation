"""
Main API entrypoint for Vercel.
This file satisfies Vercel's FastAPI detection requirements.
"""
from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    """Root API handler."""
    
    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "healthy",
            "service": "AI Code Review API",
            "version": "1.0.0",
            "endpoints": {
                "/api/webhook": "GitHub webhook handler",
                "/api/config": "Configuration API",
                "/api/install": "Installation callback"
            }
        }).encode())
