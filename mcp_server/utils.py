import subprocess
import os
import pathlib
import shutil

# Define a configurable port with a default that's less likely to conflict
DEFAULT_PORT = 5050
FLASK_PORT = int(os.environ.get("TIDAL_MCP_PORT", DEFAULT_PORT))

# Define the base URL for your Flask app using the configurable port
FLASK_APP_URL = f"http://127.0.0.1:{FLASK_PORT}"

# Define the path to the Flask app dynamically
CURRENT_DIR = pathlib.Path(__file__).parent.absolute()
FLASK_APP_PATH = os.path.join(CURRENT_DIR, "..", "tidal_api", "app.py")
FLASK_APP_PATH = os.path.normpath(FLASK_APP_PATH)  # Normalize the path

# Find the path to uv executable
def find_uv_executable():
    """Find the uv executable in the path or common locations"""
    # First try to find in PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    
    # Check common installation locations
    common_locations = [
        os.path.expanduser("~/.local/bin/uv"),  # Linux/macOS local install
        os.path.expanduser("~/AppData/Local/Programs/Python/Python*/Scripts/uv.exe"),  # Windows
        "/usr/local/bin/uv",  # macOS Homebrew
        "/opt/homebrew/bin/uv",  # macOS Apple Silicon Homebrew
    ]
    
    for location in common_locations:
        # Handle wildcards in paths
        if "*" in location:
            import glob
            matches = glob.glob(location)
            for match in matches:
                if os.path.isfile(match) and os.access(match, os.X_OK):
                    return match
        elif os.path.isfile(location) and os.access(location, os.X_OK):
            return location
    
    # If we can't find it, just return "uv" and let the system try to resolve it
    return "uv"

# Global variable to hold the Flask app process
flask_process = None

def start_flask_app():
    """Start the Flask app as a subprocess"""
    global flask_process
    
    print("Starting TIDAL Flask app...")
    
    # Find uv executable
    uv_executable = find_uv_executable()
    print(f"Using uv executable: {uv_executable}")
    
    # Start the Flask app using uv
    flask_process = subprocess.Popen([
        uv_executable, "run",
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