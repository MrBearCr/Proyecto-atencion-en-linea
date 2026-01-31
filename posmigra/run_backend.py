import sys
import os
import uvicorn
import multiprocessing

# Add the project root to sys.path to allow importing 'pal'
current_dir = os.path.dirname(os.path.abspath(__file__)) # This is <root>/posmigra/
project_root = os.path.dirname(current_dir)

# Prioritize 'posmigra' for 'app' package, then 'project_root' for 'pal'
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.append(project_root) # Append instead of insert to prioritize local app

# Also ensure 'posmigra' directory is in path so 'app' can be imported if needed
# But if we are in 'posmigra', 'import app' works directly.

if __name__ == "__main__":
    multiprocessing.freeze_support() # Needed for PyInstaller
    
    try:
        # Import the FastAPI app
        # We use a string import for uvicorn.run usually, but with PyInstaller we pass the app object
        from app.main import app
        
        # Determine port (can be passed via args or env)
        port = int(os.environ.get("PORT", 8000))
        
        print(f"Starting PAL Backend on port {port}...")
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
        
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to start backend: {e}")
        import traceback
        traceback.print_exc()
        # Keep the process alive for debugging if needed, or just exit with error
        sys.exit(1)
