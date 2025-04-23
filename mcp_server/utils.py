import subprocess
import os
import signal
import pathlib

# Define the base URL for your Flask app
FLASK_APP_URL = "http://127.0.0.1:5000"  # Change if your Flask app uses a different port

# Define the path to the Flask app
# CURRENT_DIR = pathlib.Path(__file__).parent.absolute()
# FLASK_APP_PATH = os.path.join(CURRENT_DIR, "..", "tidal_api", "app.py")
# FLASK_APP_PATH = os.path.normpath(FLASK_APP_PATH)  # Normalize the path
FLASK_APP_PATH = "/Users/yuhuacheng/Development/tidal-mcp-uv/tidal_api/app.py"

# Global variable to hold the Flask app process
flask_process = None

def start_flask_app():
    """Start the Flask app as a subprocess"""
    global flask_process
    
    print("Starting TIDAL Flask app...")
    
    # Start the Flask app using uv
    flask_process = subprocess.Popen([
        "/Users/yuhuacheng/.local/bin/uv", "run",
        "--with", "tidalapi",
        "--with", "flask",
        "--with", "requests",
        "python", FLASK_APP_PATH
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Optional: Read a few lines to ensure the app starts properly
    for _ in range(5):  # Read first 5 lines of output
        line = flask_process.stdout.readline()
        if line:
            print(f"Flask app: {line.decode().strip()}")
    
    print("TIDAL Flask app started")

def shutdown_flask_app():
    """Shutdown the Flask app subprocess when the MCP server exits"""
    global flask_process
    
    if flask_process:
        print("Shutting down TIDAL Flask app...")
        # Try to terminate gracefully first
        flask_process.terminate()
        try:
            # Wait up to 5 seconds for process to terminate
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # If it doesn't terminate in time, force kill it
            flask_process.kill()
        print("TIDAL Flask app shutdown complete")

