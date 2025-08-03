#!/usr/bin/env python3
"""
Flask Application Entry Point
Run this file to start the PromptToVideo Flask application
"""

import os
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment variables
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    print(f"🚀 Starting PromptToVideo application...")
    print(f"   Debug mode: {debug_mode}")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   URL: http://{host}:{port}")
    print(f"")
    print(f"💡 Chat System Features:")
    print(f"   - Slideout chat on video cards (index page)")
    print(f"   - Embedded chat on video watch pages")
    print(f"   - Emoji reactions and threaded replies")
    print(f"   - Test accounts: user1@test.com / user2@test.com (password: password123)")
    print(f"")
    
    # Start the Flask development server
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        threaded=True
    )