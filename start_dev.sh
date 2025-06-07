#!/bin/bash
# start_dev.sh - Updated for new project structure

echo "-------------------------------------"
echo "Starting Development Environment..."
echo "-------------------------------------"

# Start Tailwind CSS in watch mode in the background
echo "[INFO] Starting Tailwind CSS watcher..."
# The watch:css script in package.json should be:
# "tailwindcss -i ./project/static/css/src/input.css -o ./project/static/css/dist/style.css --watch"
npm run watch:css & 
TAILWIND_PID=$! 

# Wait a few seconds for Tailwind to compile initially
echo "[INFO] Waiting for initial Tailwind CSS compilation..."
sleep 5 

echo ""
echo "[INFO] Starting Flask development server..."
# Ensure FLASK_APP is set to run.py (can be in .env or Replit Secrets)
# We will run the app using 'python run.py' as run.py will configure and run the Flask app.
python run.py

FLASK_PID=$! # Get the Process ID of the Flask server (though Flask runs in foreground here)

# Optional: A function to clean up background processes when this script exits
# This might not be strictly necessary in Replit's environment as it handles process termination.
cleanup() {
    echo ""
    echo "[INFO] Shutting down development environment..."
    # Gracefully kill background processes
    if kill -0 $TAILWIND_PID > /dev/null 2>&1; then 
        echo "[INFO] Terminating Tailwind CSS watcher (PID: $TAILWIND_PID)..."
        kill $TAILWIND_PID; 
    fi
    # Flask process (FLASK_PID) should terminate when the script exits if it's the foreground process.
    # If Flask was also backgrounded, we would need:
    # if kill -0 $FLASK_PID > /dev/null 2>&1; then kill $FLASK_PID; fi
    echo "[INFO] Processes cleanup attempted."
    exit 0 # Exit gracefully
}

# Trap SIGINT (Ctrl+C) and SIGTERM to run cleanup
trap cleanup SIGINT SIGTERM

# The script will naturally exit when 'python run.py' (the foreground process) exits.
# No explicit 'wait' needed here if Flask is the last foreground command.