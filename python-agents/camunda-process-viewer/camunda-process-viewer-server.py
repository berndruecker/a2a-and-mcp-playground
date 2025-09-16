#!/usr/bin/env python3
"""
Simple CORS proxy server to bypass CORS restrictions when accessing Camunda API from browser
Also serves static files like the HTML viewer
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import sys
import os
import mimetypes
from urllib.error import HTTPError, URLError

class CORSProxyHandler(http.server.BaseHTTPRequestHandler):
    
    CAMUNDA_BASE_URL = "http://localhost:8088"
    
    def _set_cors_headers(self):
        """Set CORS headers to allow cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept')
        self.send_header('Access-Control-Max-Age', '3600')
    
    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests - serve static files or proxy to Camunda"""
        # Check if this is a request for a static file
        if self.path.startswith('/v2/'):
            # This is a Camunda API request
            self._proxy_request('GET')
        else:
            # This is a static file request
            self._serve_static_file()
    
    
    def do_POST(self):
        """Handle POST requests - only for Camunda API"""
        if self.path.startswith('/v2/'):
            self._proxy_request('POST')
        else:
            self.send_response(405)  # Method Not Allowed
            self.end_headers()
    
    def do_PUT(self):
        """Handle PUT requests - only for Camunda API"""
        if self.path.startswith('/v2/'):
            self._proxy_request('PUT')
        else:
            self.send_response(405)  # Method Not Allowed
            self.end_headers()
    
    def do_DELETE(self):
        """Handle DELETE requests - only for Camunda API"""
        if self.path.startswith('/v2/'):
            self._proxy_request('DELETE')
        else:
            self.send_response(405)  # Method Not Allowed
            self.end_headers()
    
    def _serve_static_file(self):
        """Serve static files from the current directory"""
        try:
            # Handle root path
            if self.path == '/':
                self.path = '/camunda-process-viewer.html'
            
            # Remove query parameters and decode URL
            file_path = urllib.parse.unquote(self.path.split('?')[0])
            if file_path.startswith('/'):
                file_path = file_path[1:]  # Remove leading slash
            
            # Security check - prevent directory traversal
            if '..' in file_path or file_path.startswith('/'):
                self.send_response(403)
                self.end_headers()
                return
            
            # Check if file exists
            if not os.path.isfile(file_path):
                self.send_response(404)
                self._set_cors_headers()
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<h1>404 - File Not Found</h1>')
                return
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # Read and serve the file
            with open(file_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self._set_cors_headers()
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            self.send_response(500)
            self._set_cors_headers()
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            error_html = f'<h1>500 - Server Error</h1><p>{str(e)}</p>'
            self.wfile.write(error_html.encode())
    
    
    def _proxy_request(self, method):
        """Proxy the request to Camunda API"""
        try:
            # Build the target URL
            target_url = f"{self.CAMUNDA_BASE_URL}{self.path}"
            
            # Prepare request data
            content_length = 0
            post_data = None
            
            if method in ['POST', 'PUT']:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
            
            # Create the request
            req = urllib.request.Request(target_url, data=post_data, method=method)
            
            # Copy relevant headers
            for header_name in ['Content-Type', 'Authorization', 'Accept']:
                if header_name in self.headers:
                    req.add_header(header_name, self.headers[header_name])
            
            # Make the request to Camunda
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    # Send response back to client
                    self.send_response(response.getcode())
                    self._set_cors_headers()
                    
                    # Copy response headers
                    for header, value in response.headers.items():
                        if header.lower() not in ['server', 'date', 'connection']:
                            self.send_header(header, value)
                    
                    self.end_headers()
                    
                    # Copy response body
                    self.wfile.write(response.read())
                    
            except HTTPError as e:
                # Forward HTTP errors from Camunda
                self.send_response(e.code)
                self._set_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                error_response = {
                    "error": f"Camunda API Error: {e.code}",
                    "message": str(e),
                    "url": target_url
                }
                self.wfile.write(json.dumps(error_response).encode())
                
        except URLError as e:
            # Connection error to Camunda
            self.send_response(503)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "error": "Cannot connect to Camunda",
                "message": f"Failed to connect to {self.CAMUNDA_BASE_URL}. Is Camunda running?",
                "details": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())
            
        except Exception as e:
            # General error
            self.send_response(500)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "error": "Proxy Error",
                "message": str(e),
                "type": type(e).__name__
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def log_message(self, format, *args):
        """Override to provide cleaner logging"""
        print(f"[{self.address_string()}] {format % args}")

def main():
    PORT = 3001
    
    print("=" * 60)
    print("  CAMUNDA PROCESS VIEWER - CORS PROXY SERVER")
    print("=" * 60)
    print(f"Server starting on port: {PORT}")
    print(f"Camunda API target: http://localhost:8088")
    print()
    print("📂 Static files served from current directory")
    print("🔄 API requests proxied to Camunda")
    print()
    print("🌐 Open your browser and go to:")
    print(f"   http://localhost:{PORT}")
    print(f"   http://localhost:{PORT}/camunda-process-viewer.html")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        with socketserver.TCPServer(("", PORT), CORSProxyHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Server stopped by user")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print("Make sure port 3001 is not already in use")
        sys.exit(1)

if __name__ == "__main__":
    main()
