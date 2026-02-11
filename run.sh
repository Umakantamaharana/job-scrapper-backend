#!/bin/bash
# Stop any existing Flask app or scraper instances
echo "Stopping existing processes..."
pkill -f "python3 app.py"
pkill -f "python3 scraper.py"

# Ensure dependencies are installed
# echo "Checking dependencies..."
# pip install -r requirements.txt > /dev/null 2>&1

echo "Starting Job Scraper Dashboard..."
# Run in background and save PID if needed, or just run in foreground.
# Since user asked "quickly run", foreground is often better to see output.
# But often web servers are background. Let's run in foreground so they see the URL.

python3 app.py
