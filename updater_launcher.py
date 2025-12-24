import subprocess
import sys
import time
import os

def main():
    if len(sys.argv) < 2:
        # No installer path provided, exit
        return

    installer_path = sys.argv[1]
    
    # Give the main application time to close
    time.sleep(3)

    if not os.path.exists(installer_path):
        # Installer not found, exit
        return

    # Launch the installer
    try:
        # Use start command to run detached on Windows
        subprocess.Popen(f'start "" "{installer_path}" /SILENT /CLOSEAPPLICATIONS /SUPPRESSMSGBOXES /RESTARTAPPLICATIONS', shell=True)
    except Exception:
        # If 'start' fails, try a direct launch
        try:
            subprocess.Popen([installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/SUPPRESSMSGBOXES", "/RESTARTAPPLICATIONS"])
        except Exception:
            pass # Silently fail

if __name__ == "__main__":
    main()
