import os
import subprocess
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

# These directories will be resolved from environment variables at runtime.
DATA_DIR = os.getenv("DATA_DIR", "data")
REPORT_DIR = os.getenv("REPORT_DIR", "reports")

def update_job_status(job_id, status, message=""):
    """Helper function to update the status of a job in its JSON file."""
    job_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
    if not os.path.exists(job_path):
        logging.error(f"Job file not found for {job_id} at {job_path}")
        return
        
    # Retry mechanism for file access in case of contention
    for _ in range(5):
        try:
            with open(job_path, "r+") as f:
                job_data = json.load(f)
                job_data['status'] = status
                if message:
                    job_data['status_message'] = message
                else:
                    job_data.pop('status_message', None) # Clear message if not provided
                f.seek(0)
                json.dump(job_data, f, indent=2)
                f.truncate()
            return
        except (IOError, json.JSONDecodeError) as e:
            logging.warning(f"Retrying status update for job {job_id} due to error: {e}")
            time.sleep(0.5)
    logging.error(f"Failed to update status for job {job_id} after multiple retries.")


def run_garak_scan(job_id, garak_command):
    """
    The main task function that runs a garak scan.
    This function is executed by the RQ worker.
    """
    logging.info(f"Worker picked up job: {job_id}")
    update_job_status(job_id, "running", "Garak scan has started.")

    try:
        # Ensure the reports directory exists inside the mounted volume
        if not os.path.exists(REPORT_DIR):
            os.makedirs(REPORT_DIR, exist_ok=True)
            logging.info(f"Created reports directory: {REPORT_DIR}")

        logging.info(f"Executing command for job {job_id}: {' '.join(garak_command)}")
        
        # Run the garak scan as a subprocess
        process = subprocess.Popen(
            garak_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.expanduser("~") # Run from home dir to pick up configs
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = f"Scan failed with return code {process.returncode}. Stderr: {stderr[:1000]}"
            logging.error(f"Job {job_id}: {error_message}")
            update_job_status(job_id, "failed", error_message)
        else:
            logging.info(f"Garak scan for job {job_id} completed successfully.")
            # The job status will be updated to "complete" by the web app
            # once it detects the report file. We just clear the message.
            update_job_status(job_id, "running", "Scan complete, report is being processed.")

    except Exception as e:
        error_message = f"An unexpected error occurred during the scan: {e}"
        logging.error(f"Job {job_id}: {error_message}", exc_info=True)
        update_job_status(job_id, "failed", error_message)
