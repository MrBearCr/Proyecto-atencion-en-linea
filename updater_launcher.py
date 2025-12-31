import subprocess
import sys
import time
import os
import logging

# Configurar logging para el launcher
# Se escribe en un archivo para poder revisar los logs después del cierre de la app principal
logging.basicConfig(
    filename='updater_launcher.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def wait_for_process_to_close(pid):
    """Waits for the process with the given PID to close."""
    logger.debug(f"Waiting for process with PID: {pid} to close.")
    if not pid:
        logger.debug("No PID provided to wait_for_process_to_close, performing a 3-second sleep.")
        time.sleep(3)
        return

    try:
        pid = int(pid)
    except (ValueError, TypeError):
        logger.warning(f"Invalid PID received: '{pid}'. Performing a 3-second sleep instead.")
        time.sleep(3)
        return

    for i in range(30):  # Wait for a maximum of 30 seconds
        logger.debug(f"Attempt {i+1}/30 to check PID {pid}.")
        try:
            # Use tasklist to check if the process is running
            output = subprocess.check_output(f'tasklist /FI "PID eq {pid}"', shell=True, stderr=subprocess.DEVNULL)
            if str(pid) not in str(output):
                logger.debug(f"Process with PID {pid} is no longer running.")
                return
        except subprocess.CalledProcessError as e:
            logger.debug(f"tasklist command failed for PID {pid} (likely process not found). Error: {e}")
            return # Process not found, so it's closed
        except Exception as e:
            logger.error(f"Error checking process status for PID {pid}: {e}")
            break # Exit on unexpected error
        time.sleep(1)
    logger.warning(f"Process with PID {pid} did not close within 30 seconds timeout.")


def main():
    logger.info("updater_launcher.py started.")
    logger.debug(f"Arguments received: {sys.argv}")

    if len(sys.argv) < 3:
        logger.warning("Insufficient arguments. Expected installer_path and PID. Falling back to simple delay.")
        # No installer path or PID provided, use a simple delay
        time.sleep(3)
        if len(sys.argv) < 2:
            logger.error("No installer path provided. Exiting.")
            return
        installer_path = sys.argv[1]
        pid_to_wait_for = None # No PID to wait for
    else:
        installer_path = sys.argv[1]
        pid_to_wait_for = sys.argv[2]
    
    logger.debug(f"Installer path: {installer_path}")
    logger.debug(f"PID to wait for: {pid_to_wait_for}")

    wait_for_process_to_close(pid_to_wait_for)

    if not os.path.exists(installer_path):
        logger.error(f"Installer not found at: {installer_path}. Exiting.")
        return

    logger.info(f"Launching installer: {installer_path}")
    # Launch the installer
    try:
        command = f'start "" "{installer_path}" /SILENT /CLOSEAPPLICATIONS /SUPPRESSMSGBOXES'
        logger.debug(f"Executing command (shell=True): {command}")
        subprocess.Popen(command, shell=True)
        logger.info("Installer launched successfully using 'start' command.")
    except Exception as e:
        logger.error(f"Failed to launch installer with 'start' command: {e}")
        # If 'start' fails, try a direct launch
        try:
            command_list = [installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/SUPPRESSMSGBOXES"]
            logger.debug(f"Executing command (direct Popen): {command_list}")
            subprocess.Popen(command_list)
            logger.info("Installer launched successfully using direct Popen.")
        except Exception as e_direct:
            logger.critical(f"Failed to launch installer with direct Popen: {e_direct}. Installation failed.")
            pass # Silently fail

    logger.info("updater_launcher.py finished execution.")

if __name__ == "__main__":
    main()
