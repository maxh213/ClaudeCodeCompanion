#!/usr/bin/env python3
"""
Run the Claude Agent web interface.
"""

import os
from web_interface import app

if __name__ == '__main__':
    # Create the logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Run the Flask web app
    app.run(host='0.0.0.0', port=5000, debug=True)