from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash, Response
import os
import json
import subprocess
import time
import uuid
from datetime import datetime
from threading import Thread
import glob
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'garak-dashboard-secret-key')

# Store running jobs
JOBS = {}

# Flag to control the background job status checker thread
STATUS_CHECKER_RUNNING = False

# Load existing jobs from disk
def load_existing_jobs():
    """Load existing jobs from data directory"""
    if not os.path.exists(DATA_DIR):
        return
    
    job_files = glob.glob(os.path.join(DATA_DIR, "job_*.json"))
    loaded_count = 0
    orphaned_count = 0
    
    for job_file in job_files:
        try:
            # Handle empty or corrupt job files
            if os.path.getsize(job_file) == 0:
                job_id = os.path.basename(job_file).replace('job_', '').replace('.json', '')
                logging.warning(f"Found empty job file for job {job_id}, marking as failed")
                
                # Create a minimal job entry with failed status
                JOBS[job_id] = {
                    'job_id': job_id,
                    'status': 'failed',
                    'created_at': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'output': 'Job file was corrupted or execution failed unexpectedly.'
                }
                
                # Try to recover some job info from the filename if possible
                if '_' in job_id and len(job_id.split('_')) > 1:
                    parts = job_id.split('_')
                    if len(parts) > 1:
                        JOBS[job_id]['model_name'] = parts[1]
                
                # Save the recovered job data
                with open(job_file, 'w') as f:
                    json.dump(JOBS[job_id], f)
                    
                orphaned_count += 1
                continue
                
            # Load normal job file
            with open(job_file, 'r') as f:
                job_data = json.load(f)
                
            job_id = job_data['job_id']
            JOBS[job_id] = job_data
            
            # Check for stale pending jobs (created more than 30 minutes ago)
            if job_data.get('status') == 'pending' or job_data.get('status') == 'running':
                created_time = datetime.fromisoformat(job_data.get('created_at', '2020-01-01T00:00:00'))
                if (datetime.now() - created_time).total_seconds() > 1800:  # 30 minutes
                    logging.warning(f"Job {job_id} has been pending/running for more than 30 minutes, marking as failed")
                    JOBS[job_id]['status'] = 'failed'
                    JOBS[job_id]['end_time'] = datetime.now().isoformat()
                    JOBS[job_id]['output'] = 'Job timed out or failed to complete within the expected time.'
                    
                    # Update the job file
                    with open(job_file, 'w') as f:
                        json.dump(JOBS[job_id], f)
            
            # Add report path if job is completed
            if job_data.get('status') == 'completed':
                report_jsonl = f"{job_data.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.jsonl"
                if os.path.exists(report_jsonl):
                    JOBS[job_id]['hits_path'] = report_jsonl
                    
                report_json = f"{job_data.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.json"
                if os.path.exists(report_json):
                    JOBS[job_id]['report_path'] = report_json
                    
            loaded_count += 1
            
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error loading job file {job_file}: {e}")
            try:
                # Try to recover by creating a minimal job entry
                job_id = os.path.basename(job_file).replace('job_', '').replace('.json', '')
                JOBS[job_id] = {
                    'job_id': job_id,
                    'status': 'failed',
                    'created_at': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'output': f'Job file was corrupted: {str(e)}'
                }
                # Save the recovered job data
                with open(job_file, 'w') as f:
                    json.dump(JOBS[job_id], f)
                orphaned_count += 1
            except Exception as recover_err:
                logging.error(f"Failed to recover job file {job_file}: {recover_err}")
    
    logging.info(f"Loaded {loaded_count} existing jobs from disk")
    if orphaned_count > 0:
        logging.info(f"Recovered {orphaned_count} failed or corrupted jobs")

# Configuration
# Set up environment
# Use environment variables or default to local development paths
if os.environ.get('DOCKER_ENV') == 'true':
    # Docker environment paths
    DATA_DIR = '/app/data/'
    REPORT_DIR = '/app/reports/'
else:
    # Local development paths
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')

DATA_DIR = os.environ.get('DATA_DIR', DATA_DIR)
REPORT_DIR = os.environ.get('REPORT_DIR', REPORT_DIR)

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Background thread to check job status
def check_job_status_periodically():
    """Background thread to check status of running jobs and update accordingly"""
    global STATUS_CHECKER_RUNNING
    
    try:
        logging.info("Starting background job status checker")
        while STATUS_CHECKER_RUNNING:
            # Check all jobs that are in running or pending state
            for job_id, job in dict(JOBS).items():
                if job.get('status') in ['running', 'pending']:
                    # Check if this job has completed based on report files
                    report_json = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.json"
                    report_jsonl = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.jsonl"
                    hitlog_jsonl = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.hitlog.jsonl"
                    
                    reports_exist = os.path.exists(report_json) or os.path.exists(report_jsonl)
                    
                    # If we have report files but job status is still running, update it
                    if reports_exist and job.get('status') in ['running', 'pending']:
                        logging.info(f"Job {job_id} has report files but status is {job.get('status')}, updating to completed")
                        JOBS[job_id]['status'] = 'completed'
                        JOBS[job_id]['end_time'] = datetime.now().isoformat()
                        
                        # Calculate job duration
                        if 'start_time' in JOBS[job_id]:
                            try:
                                start_time = datetime.fromisoformat(JOBS[job_id]['start_time'])
                                end_time = datetime.fromisoformat(JOBS[job_id]['end_time'])
                                duration_seconds = (end_time - start_time).total_seconds()
                                JOBS[job_id]['duration'] = duration_seconds
                            except Exception as e:
                                logging.error(f"Error calculating job duration: {str(e)}")
                        
                        # Set report paths
                        if os.path.exists(report_json):
                            JOBS[job_id]['report_path'] = report_json
                        if os.path.exists(report_jsonl):
                            JOBS[job_id]['hits_path'] = report_jsonl
                        
                        # Update job file on disk
                        job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
                        try:
                            with open(job_file_path, 'w') as f:
                                json.dump(JOBS[job_id], f)
                            logging.info(f"Updated job file for {job_id} with completed status")
                        except Exception as e:
                            logging.error(f"Error updating job file for {job_id}: {str(e)}")
                    
                    # Check for stalled jobs (running for too long)
                    elif job.get('status') in ['running', 'pending'] and 'start_time' in job:
                        try:
                            start_time = datetime.fromisoformat(job['start_time'])
                            current_time = datetime.now()
                            running_time = (current_time - start_time).total_seconds()
                            
                            # If running more than 30 minutes, mark as potentially stalled
                            if running_time > 1800:  # 30 minutes
                                logging.warning(f"Job {job_id} has been running for {running_time/60:.1f} minutes and may be stalled")
                                
                                # Update job progress if available
                                if os.path.exists(hitlog_jsonl):
                                    # Try to estimate progress from hitlog
                                    try:
                                        with open(hitlog_jsonl, 'r') as f:
                                            completed_items = sum(1 for _ in f)
                                        # Store progress information
                                        if 'total_items' in job:
                                            progress_pct = min(100, (completed_items / job['total_items']) * 100)
                                            JOBS[job_id]['progress'] = {
                                                'completed': completed_items,
                                                'total': job['total_items'],
                                                'percent': progress_pct
                                            }
                                    except Exception as e:
                                        logging.error(f"Error reading hitlog for {job_id}: {str(e)}")
                        except Exception as e:
                            logging.error(f"Error checking job staleness for {job_id}: {str(e)}")
                    
                    # Update progress information for running jobs
                    if job.get('status') in ['running', 'pending'] and os.path.exists(hitlog_jsonl):
                        try:
                            with open(hitlog_jsonl, 'r') as f:
                                completed_items = sum(1 for _ in f)
                            
                            # If total_items not set, try to estimate from job config
                            if 'total_items' not in job:
                                # Get probe count - rough estimate based on number of probes and typical prompts per probe
                                probe_count = len(job.get('probes', []))
                                estimated_total = probe_count * 15  # Rough estimate of prompts per probe
                                JOBS[job_id]['total_items'] = estimated_total
                            
                            # Store progress information
                            total_items = job.get('total_items', 100)  # Default to 100 if we can't estimate
                            progress_pct = min(100, (completed_items / total_items) * 100)
                            JOBS[job_id]['progress'] = {
                                'completed': completed_items,
                                'total': total_items,
                                'percent': progress_pct
                            }
                            
                            # Estimate time remaining
                            if 'start_time' in job:
                                try:
                                    start_time = datetime.fromisoformat(job['start_time'])
                                    current_time = datetime.now()
                                    elapsed_seconds = (current_time - start_time).total_seconds()
                                    
                                    # Only estimate if we have some progress
                                    if progress_pct > 0 and elapsed_seconds > 5:
                                        seconds_per_percent = elapsed_seconds / progress_pct
                                        remaining_seconds = seconds_per_percent * (100 - progress_pct)
                                        JOBS[job_id]['progress']['remaining_seconds'] = remaining_seconds
                                        JOBS[job_id]['progress']['elapsed_seconds'] = elapsed_seconds
                                except Exception as e:
                                    logging.error(f"Error calculating time remaining for {job_id}: {str(e)}")
                                    
                        except Exception as e:
                            logging.error(f"Error updating progress for {job_id}: {str(e)}")
            
            # Sleep for a few seconds before checking again
            time.sleep(10)
            
    except Exception as e:
        logging.error(f"Error in job status checker: {str(e)}")
    finally:
        logging.info("Job status checker thread stopping")

# Start the background job checker thread
def start_job_status_checker():
    global STATUS_CHECKER_RUNNING
    if not STATUS_CHECKER_RUNNING:
        STATUS_CHECKER_RUNNING = True
        checker_thread = Thread(target=check_job_status_periodically)
        checker_thread.daemon = True
        checker_thread.start()
        logging.info("Started job status checker thread")
    else:
        logging.info("Job status checker already running")

# Now load existing jobs after directories are defined
load_existing_jobs()

# Start the job status checker thread
start_job_status_checker()

# Available generators (model hubs)
GENERATORS = {
    'openai': 'OpenAI',
    'huggingface': 'HuggingFace',
    'cohere': 'Cohere',
    'anthropic': 'Anthropic',
    'ollama': 'Ollama',
    'replicate': 'Replicate',
    'vertexai': 'Google VertexAI',
    'llamacpp': 'LlamaCPP'
}

# Category to probe mapping
PROBE_CATEGORIES = {
    'security': [
        'dan.Ablation_Dan_11_0',
        'dan.AutoDANCached',
        'dan.DanInTheWild',
        'promptinject.HijackHateHumans',
        'promptinject.HijackKillHumans',
        'promptinject.HijackLongPrompt',
        'xss.ColabAIDataLeakage',
        'xss.MarkdownImageExfil',
        'xss.MdExfil20230929',
        'xss.StringAssemblyDataExfil'
    ],
    'privacy': [
        'leakreplay.GuardianCloze',
        'leakreplay.GuardianComplete',
        'leakreplay.LiteratureCloze',
        'leakreplay.LiteratureComplete',
        'leakreplay.NYTCloze',
        'leakreplay.NYTComplete',
        'leakreplay.PotterCloze',
        'leakreplay.PotterComplete'
    ],
    'toxicity': [
        'grandma.Slurs',
        'grandma.Substances',
        'lmrc.Bullying',
        'lmrc.Deadnaming',
        'lmrc.QuackMedicine',
        'lmrc.SexualContent',
        'lmrc.Sexualisation',
        'lmrc.SlurUsage',
        'realtoxicityprompts.RTPBlank'
    ],
    'hallucination': [
        'misleading.FalseAssertion',
        'packagehallucination.JavaScript',
        'packagehallucination.Python',
        'packagehallucination.Ruby',
        'packagehallucination.Rust'
    ],
    'performance': [
        'continuation.ContinueSlursReclaimedSlurs',
        'divergence.Repeat',
        'phrasing.FutureTense',
        'phrasing.PastTense',
        'snowball.GraphConnectivity'
    ],
    'robustness': [
        'encoding.InjectAscii85',
        'encoding.InjectBase64',
        'encoding.InjectROT13',
        'encoding.InjectZalgo',
        'glitch.Glitch'
    ],
    'ethics': [
        'latentinjection.LatentInjectionReport',
        'latentinjection.LatentInjectionResume',
        'latentinjection.LatentJailbreak',
        'latentinjection.LatentWhois'
    ],
    'stereotype': [
        'topic.WordnetControversial'
    ]
}

def run_garak_job(job_id, generator, model_name, probes, api_keys):
    # Import needed modules - moved all imports to the beginning
    import subprocess
    
    try:
        # Create a job configuration dictionary for tracking
        job_config = {
            'job_id': job_id,
            'generator': generator,
            'model_name': model_name,
            'probes': probes,
            'api_keys': api_keys,
            'report_prefix': os.path.join(REPORT_DIR, job_id),
        }
        
        # Save job config for reference
        job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
        with open(job_file_path, 'w') as f:
            json.dump(job_config, f)
            
        logging.info(f"Created job file: {job_file_path}")
        
        # Update job status to running
        JOBS[job_id]['status'] = 'running'
        JOBS[job_id]['start_time'] = datetime.now().isoformat()
        
        # Update the job file with running status
        with open(job_file_path, 'w') as f:
            json.dump(JOBS[job_id], f)
        
        # Format probes for command line
        # Handle categories parameter which is passed as 'probes'
        if isinstance(probes, list) and probes:
            # If the input is a list of category names like ['encoding'], map them to actual probe names
            if probes[0] in PROBE_CATEGORIES:
                # Get probes for each category
                probe_list = []
                for category in probes:
                    if category in PROBE_CATEGORIES:
                        probe_list.extend(PROBE_CATEGORIES[category])
                probe_str = ",".join(probe_list)
            else:
                # If the input is already a list of probe names
                probe_str = ",".join(probes)
        else:
            # Default to a basic encoding probe if no probes specified
            probe_str = "encoding.InjectBase64"
        
        # Create a bash script to run garak CLI command
        report_prefix = os.path.join(REPORT_DIR, job_id)
        script_content = """#!/bin/bash

# Set environment variables for API keys
"""
        
        # Add API keys to environment variables
        test_mode = False
        for key, value in api_keys.items():
            if value:  # Only set if value is not empty
                # Detect if we're using test keys
                if value in ['test_key', 'test', 'dummy', 'sk-test']:
                    test_mode = True
                    logging.warning(f"Using test API key for {key} - real API calls will fail")
                script_content += f"export {key.upper()}='{value}'\n"
        
        # Construct the garak CLI command
        if test_mode:
            # In test mode, use a special configuration that doesn't require valid API keys
            # This provides better feedback than just failing with auth errors
            cmd_str = f"garak --model_type huggingface --model_name gpt2 --probes encoding.InjectBase64 --generations 1 --report_prefix {report_prefix} --detector_options '{{\\\"-a\\\":\\\"test_mode\\\"}}'"  
            logging.info(f"Using test mode configuration for job {job_id} - will use local HF model instead of {generator}")
        else:
            # Normal mode with actual API keys
            cmd_str = f"garak --model_type {generator} --model_name {model_name} --probes {probe_str} --generations 1 --report_prefix {report_prefix}"
        
        script_content += f"""

echo "Running Garak scan with command: {cmd_str}"
{cmd_str} 2>&1

EXIT_CODE=$?
echo "Garak scan completed with exit code: $EXIT_CODE"
exit $EXIT_CODE
"""
        
        # Write the script to a file
        script_path = f"/tmp/garak_job_{job_id}.sh"
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        # Run the script as a subprocess and capture output
        process = subprocess.Popen([script_path], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        
        # Wait for the process to complete and capture output
        stdout, stderr = process.communicate()
        return_code = process.returncode
        
        # Save stdout and stderr to files for debugging
        stdout_path = os.path.join(REPORT_DIR, f"{job_id}_stdout.log")
        stderr_path = os.path.join(REPORT_DIR, f"{job_id}_stderr.log")
        
        with open(stdout_path, "wb") as f:
            f.write(stdout)
            
        with open(stderr_path, "wb") as f:
            f.write(stderr)
        
        # Set report file paths
        report_json_path = f"{report_prefix}.report.json"
        report_jsonl_path = f"{report_prefix}.report.jsonl"
        
        # Combine stdout and stderr for better display
        JOBS[job_id]['output'] = ''
        if stdout:
            JOBS[job_id]['output'] += stdout.decode('utf-8', errors='replace')
        if stderr:
            # Add a separator if we have both stdout and stderr
            if stdout:
                JOBS[job_id]['output'] += '\n\n---ERROR OUTPUT---\n'
            JOBS[job_id]['output'] += stderr.decode('utf-8', errors='replace')
            
        # Set end time and return code
        JOBS[job_id]['end_time'] = datetime.now().isoformat()
        JOBS[job_id]['return_code'] = return_code
        
        # Check if report files actually exist before setting paths
        has_reports = False
        if os.path.exists(report_json_path):
            JOBS[job_id]['report_path'] = report_json_path
            has_reports = True
        if os.path.exists(report_jsonl_path):
            JOBS[job_id]['hits_path'] = report_jsonl_path
            has_reports = True
        
        # If return code is successful but no reports are found, treat as failure
        if return_code == 0 and not has_reports:
            logging.error(f"Job {job_id} completed successfully but no report files were generated")
            JOBS[job_id]['output'] += '\n\nWARNING: Job completed successfully but no report files were generated.'
            JOBS[job_id]['status'] = 'failed'
            return_code = 1  # Mark as failure
        else:
            # Set job status based on return code
            JOBS[job_id]['status'] = 'completed' if return_code == 0 else 'failed'
        
        # Add specific error message based on error output if job failed
        if return_code != 0:
            error_text = stderr.decode('utf-8', errors='replace').strip() if stderr else ''
            if 'unauthorized' in error_text.lower() or 'api key' in error_text.lower():
                JOBS[job_id]['output'] += '\n\nERROR: API authorization failed. Please check that you have provided valid API credentials.'
            elif not error_text:
                JOBS[job_id]['output'] += f'\n\nERROR: Job failed with return code {return_code}.'
        
        # Update job config with all the status information
        job_config.update({
            'status': JOBS[job_id]['status'],
            'end_time': JOBS[job_id]['end_time'],
            'return_code': return_code,
            'output': JOBS[job_id]['output']
        })
        
        if 'report_path' in JOBS[job_id]:
            job_config['report_path'] = JOBS[job_id]['report_path']
        if 'hits_path' in JOBS[job_id]:
            job_config['hits_path'] = JOBS[job_id]['hits_path']
            
        # Write updated job status to disk
        with open(job_file_path, 'w') as f:
            json.dump(job_config, f)
            
        logging.info(f"Job {job_id} completed with status {job_config['status']}")
        if job_config['status'] == 'failed':
            logging.error(f"Job {job_id} failed with return code {return_code}")
        
        # Make sure all updated fields are in both memory (JOBS) and disk (job_config)
        
        logging.info(f"Job {job_id} completed with status {JOBS[job_id]['status']}")
        return JOBS[job_id]
        
    except Exception as e:
        logging.error(f"Error in job {job_id}: {str(e)}")
        # Ensure the job is marked as failed
        JOBS[job_id]['status'] = 'failed'
        JOBS[job_id]['output'] = f"Job failed with an unexpected error: {str(e)}"
        JOBS[job_id]['end_time'] = datetime.now().isoformat()
        
        # Make sure to persist the failure to disk
        job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
        if os.path.exists(job_file_path):
            try:
                # Try to read the existing job file
                with open(job_file_path, 'r') as f:
                    job_config = json.load(f)
            except:
                # If job file can't be read, create a new minimal config
                job_config = {
                    'job_id': job_id,
                    'created_at': datetime.now().isoformat()
                }
                
            # Update with error information
            job_config.update({
                'status': 'failed',
                'end_time': JOBS[job_id]['end_time'],
                'output': JOBS[job_id]['output']
            })
            
            # Write back to disk
            try:
                with open(job_file_path, 'w') as f:
                    json.dump(job_config, f)
            except Exception as write_error:
                logging.error(f"Failed to write error status to job file for {job_id}: {str(write_error)}")
        
        return JOBS[job_id]

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', 
                           generators=GENERATORS, 
                           probe_categories=PROBE_CATEGORIES)

@app.route('/jobs')
def jobs():
    """View all jobs"""
    return render_template('jobs.html', jobs=JOBS)

@app.route('/job/<job_id>')
def job_detail(job_id):
    """View job details"""
    if job_id not in JOBS:
        return "Job not found", 404
    
    job = JOBS[job_id]
    
    # Load HTML report if it exists
    html_report_content = None
    html_report_path = os.path.join(REPORT_DIR, f"{job_id}.report.html")
    if os.path.exists(html_report_path):
        try:
            with open(html_report_path, 'r', encoding='utf-8') as f:
                html_report_content = f.read()
        except Exception as e:
            logging.error(f"Error reading HTML report: {str(e)}")
    
    # Before processing, check job status from both memory and disk to ensure consistency
    # This helps fix any jobs that might have inconsistent status between database and UI
    job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
    if os.path.exists(job_file_path):
        try:
            with open(job_file_path, 'r') as f:
                job_from_disk = json.load(f)
                
            # If disk shows a different status than memory, prefer the disk version
            # This ensures consistency between API status and displayed status
            if job_from_disk.get('status') != job.get('status'):
                logging.info(f"Correcting inconsistent status for job {job_id}: memory={job.get('status')}, disk={job_from_disk.get('status')}")
                job['status'] = job_from_disk.get('status')
                if 'output' in job_from_disk:
                    job['output'] = job_from_disk.get('output')
        except Exception as e:
            logging.error(f"Error reading job file for status check: {str(e)}")
    
    # Handle jobs that don't have output field based on their status
    if 'output' not in job:
        if job.get('status') == 'completed':
            # Check if the report exists
            report_jsonl_path = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.jsonl"
            report_json_path = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.json"
            
            has_reports = False
            if os.path.exists(report_jsonl_path):
                # Add the hits path if it doesn't exist
                if 'hits_path' not in job:
                    job['hits_path'] = report_jsonl_path
                has_reports = True
                    
            if os.path.exists(report_json_path):
                # Add the report path if it doesn't exist
                if 'report_path' not in job:
                    job['report_path'] = report_json_path
                has_reports = True
                
            # Add appropriate output message
            if has_reports:
                job['output'] = f"Garak scan completed successfully. Report available at: {report_json_path}\n\nTo view report contents, download using the buttons on the left."
            else:
                # Mark as failed if completed but no reports
                job['output'] = "Job appears completed but no report files were found. The job may have failed."
                job['status'] = 'failed'
                # Update job file to persist this change
                job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
                if os.path.exists(job_file_path):
                    try:
                        with open(job_file_path, 'r') as f:
                            job_config = json.load(f)
                        job_config['status'] = 'failed'
                        job_config['output'] = job['output']
                        with open(job_file_path, 'w') as f:
                            json.dump(job_config, f)
                    except Exception as e:
                        logging.error(f"Failed to update job file for {job_id}: {str(e)}")
        
        elif job.get('status') == 'failed':
            # For failed jobs without output, add a default error message
            job['output'] = "Job failed. No detailed error information available."
            
        elif job.get('status') == 'running' or job.get('status') == 'pending':
            # For running or pending jobs, show appropriate message
            job['output'] = "Job is still running. Output will appear here when available."
            
            # Check if job has been running too long (more than 30 minutes)
            if 'start_time' in job:
                try:
                    start_time = datetime.fromisoformat(job['start_time'])
                    current_time = datetime.now()
                    # If job has been running for more than 30 minutes, mark as potentially stalled
                    if (current_time - start_time).total_seconds() > 1800:  # 30 minutes
                        job['output'] += "\n\nWARNING: This job has been running for more than 30 minutes and may be stalled."
                except:
                    pass
        else:
            # Default case for unknown status
            job['output'] = "No output logs available for this job."
    
    return render_template('job_detail.html', job=JOBS[job_id], job_id=job_id, html_report=html_report_content)

@app.route('/api/start_job', methods=['POST'])
def start_job():
    """API endpoint to start a new Garak job"""
    data = request.json
    generator = data.get('generator')
    model_name = data.get('model_name')
    selected_categories = data.get('categories', [])
    api_keys = data.get('api_keys', {})
    
    # Validate inputs
    if not generator or not model_name:
        return jsonify({'status': 'error', 'message': 'Generator and model name are required'}), 400
    
    # Create a unique job ID
    job_id = str(uuid.uuid4())
    
    # Collect all probes from selected categories
    selected_probes = []
    for category in selected_categories:
        if category in PROBE_CATEGORIES:
            selected_probes.extend(PROBE_CATEGORIES[category])
    
    # Create job entry
    JOBS[job_id] = {
        'id': job_id,
        'generator': generator,
        'model_name': model_name,
        'probes': selected_probes,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'api_keys': {k: '***' for k, v in api_keys.items() if v}  # Don't store actual keys in job history
    }
    
    # Start job in background thread
    thread = threading.Thread(
        target=run_garak_job, 
        args=(job_id, generator, model_name, selected_probes, api_keys)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'message': f'Job started with ID: {job_id}'
    })

@app.route('/api/job_status/<job_id>')
def job_status(job_id):
    """Get status of a specific job"""
    if job_id not in JOBS:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404
    return jsonify({
        'status': 'success',
        'job': JOBS[job_id]
    })

@app.route('/download/<job_id>/<file_type>')
def download_report(job_id, file_type):
    """Download job report or hits file"""
    try:
        if job_id not in JOBS:
            return "Job not found", 404
        
        job = JOBS[job_id]
        
        # Determine file path based on type
        if file_type == 'report':
            # Check if report_path exists in job data
            if 'report_path' not in job:
                # Try multiple possible extensions
                possible_extensions = [".report.jsonl", ".report.json"]
                found = False
                for ext in possible_extensions:
                    report_path = os.path.join(REPORT_DIR, f"{job_id}{ext}")
                    if os.path.exists(report_path):
                        file_path = report_path
                        found = True
                        break
                
                if not found:
                    logging.error(f"Report file not found for job {job_id}. No report_path in job data and could not find report with any known extension.")
                    return "Report file not found", 404
            else:
                file_path = job['report_path']
                
            # Set appropriate filename based on actual file extension
            if file_path.endswith('.jsonl'):
                filename = f"garak_report_{job_id}.jsonl"
            else:
                filename = f"garak_report_{job_id}.json"
            
        elif file_type == 'hits':
            # Check if hits_path exists in job data
            if 'hits_path' not in job:
                # Try multiple possible extensions
                possible_extensions = [".hitlog.jsonl", ".hitlog.json"]
                found = False
                for ext in possible_extensions:
                    hits_path = os.path.join(REPORT_DIR, f"{job_id}{ext}")
                    if os.path.exists(hits_path):
                        file_path = hits_path
                        found = True
                        break
                
                if not found:
                    logging.error(f"Hits file not found for job {job_id}. No hits_path in job data and could not find hits file with any known extension.")
                    return "Hits file not found", 404
            else:
                file_path = job['hits_path']
                
            # Set appropriate filename based on actual file extension
            if file_path.endswith('.jsonl'):
                filename = f"garak_hits_{job_id}.jsonl"
            else:
                filename = f"garak_hits_{job_id}.json"
        else:
            return "Invalid file type. Must be 'report' or 'hits'.", 400
        
        # Final check to ensure file exists
        if not os.path.exists(file_path):
            logging.error(f"File not found at path {file_path} for job {job_id}")
            return f"File not found: {file_type}", 404
        
        # Attempt to send the file with proper error handling
        try:
            return send_file(file_path, as_attachment=True, download_name=filename)
        except Exception as e:
            logging.error(f"Error sending file {file_path} for download: {str(e)}")
            return f"Error processing download: {str(e)}", 500
    except Exception as e:
        logging.error(f"Unexpected error in download_report: {str(e)}")
        return f"Server error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
