from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash, Response
import os
import json
import subprocess
import time
import uuid
import re
from datetime import datetime, timedelta
from threading import Thread
import glob
import threading
import logging
import jsonlines

# Import authentication module
from dashboard import auth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'garak-dashboard-secret-key')

# Initialize Firebase
with app.app_context():
    try:
        firebase_app = auth.init_firebase_admin()
        if not firebase_app:
            app.logger.error("Failed to initialize Firebase Admin SDK. Check logs for details.")
        else:
            app.logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing Firebase: {str(e)}", exc_info=True)
        firebase_app = None

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
            
            # Handle both 'id' and 'job_id' field names for compatibility
            if 'id' in job_data and 'job_id' not in job_data:
                job_data['job_id'] = job_data['id']
                job_id = job_data['id']
            elif 'job_id' in job_data and 'id' not in job_data:
                job_data['id'] = job_data['job_id']
                job_id = job_data['job_id']
            elif 'job_id' in job_data:
                job_id = job_data['job_id']
            else:
                # Extract job ID from filename as fallback
                job_id = os.path.basename(job_file).replace('job_', '').replace('.json', '')
                job_data['id'] = job_id
                job_data['job_id'] = job_id
                logging.warning(f"Job file {job_file} missing both 'id' and 'job_id' fields, using filename: {job_id}")
                
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
                    'id': job_id,  # Include both id and job_id for consistency
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
                    report_html = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.html"
                    
                    # Only consider reports to exist if the HTML report is also present
                    # This is critical as the HTML report is the final output generated
                    reports_exist = os.path.exists(report_html) and (os.path.exists(report_json) or os.path.exists(report_jsonl))
                    
                    # Check if the job is ACTUALLY complete, not just if report files exist
                    # Report files can exist while the job is still in progress!
                    if reports_exist and job.get('status') in ['running', 'pending']:
                        # Check if the output contains evidence that Garak is actually finished
                        is_garak_finished = False
                        
                        # First check if this job has output indicating completion
                        if 'output' in job and job['output']:
                            output = job['output']
                            
                            # Check for completion indicators
                            completion_indicators = [
                                'Garak scan completed with exit code: 0',
                                '100%|██████████| ',
                                'Reports saved to'
                            ]
                            
                            for indicator in completion_indicators:
                                if indicator in output:
                                    is_garak_finished = True
                                    logging.info(f'Found completion indicator for job {job_id}: "{indicator}"')
                                    break
                            
                            # Check if any progress indicators are in recent output
                            if not is_garak_finished:
                                progress_patterns = [
                                    r'\d+%\|',  # Progress bar pattern
                                    r'\[\d+:\d+<\d+:\d+',  # Time remaining pattern
                                    r'Running probe',
                                    r'Processing results',
                                    r'it/s',  # iterations per second
                                    r'\d+/\d+'  # X of Y pattern
                                ]
                                
                                recent_output = output[-5000:] if len(output) > 5000 else output
                                has_progress_indicators = False
                                
                                for pattern in progress_patterns:
                                    if re.search(pattern, recent_output):
                                        has_progress_indicators = True
                                        logging.info(f'Job {job_id} still shows progress indicators, not marking as complete yet')
                                        break
                                
                                # ONLY consider a job complete if we found explicit completion indicators
                                # The lack of progress indicators alone is NOT sufficient to mark a job as complete
                                # This prevents premature completion marking
                        
                        # Only update to completed if we have explicit completion indicators
                        if is_garak_finished:
                            logging.info(f"Job {job_id} appears to be complete, updating status from {job.get('status')}")
                            JOBS[job_id]['status'] = 'completed'
                            
                            # Only set end_time if not already set
                            if 'end_time' not in JOBS[job_id]:
                                JOBS[job_id]['end_time'] = datetime.now().isoformat()
                                
                            # Also verify report files have actual content (including HTML report)
                            if (os.path.exists(report_json) and os.path.getsize(report_json) < 10) or \
                               (os.path.exists(report_html) and os.path.getsize(report_html) < 100):
                                logging.warning(f"Report file(s) for job {job_id} exist but appear empty/incomplete, not marking as complete")
                                JOBS[job_id]['status'] = 'running'  # Revert status
                        else:
                            logging.info(f"Job {job_id} has report files but appears to still be running, keeping status as {job.get('status')}")
                        
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
    'llamacpp': 'LlamaCPP',
    'mistral': 'Mistral',
    'litellm': 'LiteLLM'
}

# List of Anthropic models available via LiteLLM
ANTHROPIC_MODELS = [
    # Claude 4 models
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    # Claude 3.7 models
    "claude-3-7-sonnet-20250219",
    # Claude 3.5 models
    "claude-3-5-opus-20241003",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20241022",
    # Claude 3 models
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    # Legacy Claude models
    "claude-2.1",
    "claude-2.0",
    "claude-instant-1.2"
]

# Category to probe mapping
PROBE_CATEGORIES = {
    'dan': [
        'dan.Ablation_Dan_11_0',
        'dan.AntiDAN',
        'dan.DAN_Jailbreak',
        'dan.Dan_10_0',
        'dan.Dan_11_0',
        'dan.Dan_6_0',
        'dan.Dan_6_2',
        'dan.Dan_7_0',
        'dan.Dan_8_0',
        'dan.Dan_9_0',
        'dan.DUDE',
        'dan.STAN',
        'dan.DanInTheWild',
        'dan.DanInTheWildFull',
        'dan.AutoDAN',
        'dan.AutoDANCached',
        'dan.ChatGPT_Image_Markdown',
        'dan.ChatGPT_Developer_Mode_RANTI',
        'dan.ChatGPT_Developer_Mode_v2'
    ],
    'security': [
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

def run_garak_job(job_id, generator, model_name, probes, api_keys, parallel_attempts=1):
    # Import needed modules - moved all imports to the beginning
    import subprocess, threading, io, select
    
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
        if isinstance(probes, list) and probes:
            # The 'probes' argument is a list of individual probe names expanded from categories.
            probe_str = ",".join(probes)
            logging.info(f"Job {job_id}: Using probes: {probe_str}")
        else:
            # Default to a basic encoding probe if no probes are specified
            logging.warning(f"No probes selected for job {job_id}, defaulting to encoding.InjectBase64")
            probe_str = "encoding.InjectBase64"
        
        # Create a bash script to run garak CLI command
        report_prefix = os.path.join(REPORT_DIR, job_id)
        script_content = """#!/bin/bash

# Set environment variables for API keys
"""
        
        # Add API keys to environment variables
        # Determine if we should be in test mode. Test mode is only enabled when a generator
        # that requires API keys is selected, but no keys are provided.
        KEY_REQUIRED_GENERATORS = ['openai', 'cohere', 'anthropic', 'replicate', 'vertexai', 'mistral', 'litellm', 'gemini']
        logging.info(f"Job {job_id}: Generator: {generator}, API keys received: {list(api_keys.keys())}")
        
        # Debug the API keys values (without revealing actual keys)
        has_api_keys = {k: (v and len(v) > 0) for k, v in api_keys.items()}
        logging.info(f"Job {job_id}: Has API keys: {has_api_keys}")
        
        # Explicitly check for the specific key needed for this generator
        key_needed = None
        if generator == 'openai': key_needed = 'openai_api_key'
        elif generator == 'anthropic': key_needed = 'anthropic_api_key'
        elif generator == 'cohere': key_needed = 'cohere_api_key'
        elif generator == 'vertexai': key_needed = 'gcp_credentials_path'
        elif generator == 'mistral': key_needed = 'mistral_api_key'
        elif generator == 'replicate': key_needed = 'replicate_api_token'
        elif generator == 'gemini': key_needed = 'google_api_key'
        elif generator == 'litellm': key_needed = 'anthropic_api_key'  # LiteLLM with Anthropic models uses the Anthropic API key
        
        if generator in KEY_REQUIRED_GENERATORS:
            # For key-requiring generators, check if we have the specific key needed
            if key_needed and key_needed in api_keys and api_keys[key_needed]:
                logging.info(f"Job {job_id}: Required API key '{key_needed}' is provided for {generator}.")
                test_mode = False
            else:
                logging.warning(f"Job {job_id}: Required API key '{key_needed}' is missing for {generator}. Enabling test mode.")
                test_mode = True
        else:
            # For local models that don't need keys
            logging.info(f"Job {job_id}: Generator {generator} doesn't require API keys. Test mode disabled.")
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
            cmd_str = f"python3 -m garak --model_type huggingface --model_name gpt2 --probes encoding.InjectBase64 --generations 1 --report_prefix {report_prefix} --detector_options '{{\"-a\":\"test_mode\"}}'"
            logging.info(f"Using test mode configuration for job {job_id} - will use local HF model instead of {generator}")
        else:
            # Normal mode with actual API keys
            cmd_str = f"python3 -m garak --model_type {generator} --model_name \"{model_name}\" --probes {probe_str} --report_prefix {report_prefix}"
            if model_name.startswith('o3'):
                cmd_str += " -m openai.OpenAIReasoningGenerator"
            try:
                if int(parallel_attempts) > 1:
                    cmd_str += f" --parallel_attempts {int(parallel_attempts)}"
            except (ValueError, TypeError):
                pass
            logging.info(f"Job {job_id}: Executing command: {cmd_str}")
        
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
        
        # Create output file for streaming
        live_output_path = os.path.join(REPORT_DIR, f"{job_id}_live_output.txt")
        with open(live_output_path, "w") as f:
            f.write("Starting Garak job...\n")
        
        # Run the script as a subprocess with streaming output
        process = subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )
        
        # Store process ID for status checking
        JOBS[job_id]['process_id'] = process.pid
        
        # Function to handle streaming output
        def stream_output():
            try:
                # Initialize buffers for stdout and stderr
                output_buffer = ""
                
                # Open output file for streaming
                with open(live_output_path, "a") as output_file:
                    # While the process is running
                    while process.poll() is None:
                        # Check if there's output to read from stdout
                        if process.stdout in select.select([process.stdout], [], [], 0.1)[0]:
                            line = process.stdout.readline()
                            if line:
                                output_buffer += line
                                output_file.write(line)
                                output_file.flush()
                        
                        # Check if there's output to read from stderr
                        if process.stderr in select.select([process.stderr], [], [], 0.1)[0]:
                            line = process.stderr.readline()
                            if line:
                                output_buffer += f"ERROR: {line}"
                                output_file.write(f"ERROR: {line}")
                                output_file.flush()
                        
                        # Update the job output in memory
                        if output_buffer:
                            JOBS[job_id]['output'] = output_buffer
                            
                            # Update the job file periodically
                            try:
                                with open(job_file_path, "w") as job_file:
                                    json.dump(JOBS[job_id], job_file)
                            except Exception as e:
                                logging.error(f"Failed to update job file: {str(e)}")
                    
                    # Process has ended, capture any remaining output
                    stdout, stderr = process.communicate()
                    if stdout:
                        output_buffer += stdout
                        output_file.write(stdout)
                    if stderr:
                        output_buffer += f"ERROR: {stderr}"
                        output_file.write(f"ERROR: {stderr}")
                
                # Get the return code
                return_code = process.returncode
                
                # Set report file paths
                report_json_path = f"{report_prefix}.report.json"
                report_jsonl_path = f"{report_prefix}.report.jsonl"
                
                # Update job with final information
                JOBS[job_id]['output'] = output_buffer
                JOBS[job_id]['return_code'] = return_code
                JOBS[job_id]['end_time'] = datetime.now().isoformat()
                
                # Check if report files exist
                has_reports = False
                if os.path.exists(report_json_path):
                    JOBS[job_id]['report_path'] = report_json_path
                    has_reports = True
                if os.path.exists(report_jsonl_path):
                    JOBS[job_id]['hits_path'] = report_jsonl_path
                    has_reports = True
                
                # Set job status based on return code, report existence, and check if output indicates completion
                is_garak_finished = True
                
                # Check if the output contains evidence that Garak is actually finished
                if output_buffer:
                    # Look for patterns indicating job is still in progress
                    progress_patterns = [
                        r'\d+%\|\s+\| \d+/\d+ \[\d+:\d+<\d+:\d+',  # Progress bar pattern
                        r'Running probe',
                        r'Processing results'
                    ]
                    
                    # If any recent output shows progress indicators, don't mark as complete
                    recent_output = output_buffer[-5000:] if len(output_buffer) > 5000 else output_buffer
                    for pattern in progress_patterns:
                        if re.search(pattern, recent_output):
                            # Still showing progress indicators, not finished
                            is_garak_finished = False
                            logging.info(f'Job {job_id} shows progress indicators, not marking as complete yet')
                            break
                    
                    # Look for specific completion indicators
                    completion_indicators = [
                        'Garak scan completed with exit code: 0',
                        '100%|██████████| ',
                        'Reports saved to'
                    ]
                    
                    # If we're not sure it's finished, look for completion indicators
                    if not is_garak_finished:
                        for indicator in completion_indicators:
                            if indicator in recent_output:
                                is_garak_finished = True
                                logging.info(f'Found completion indicator for job {job_id}: {indicator}')
                                break
                
                # Only mark as complete if process exited successfully, reports exist, and output indicates completion
                if return_code == 0 and has_reports and is_garak_finished:
                    JOBS[job_id]['status'] = 'completed'
                    logging.info(f'Job {job_id} marked as completed')
                elif return_code != 0:
                    JOBS[job_id]['status'] = 'failed'
                    logging.info(f'Job {job_id} marked as failed with return code {return_code}')
                else:
                    # If process exited with code 0 but doesn't seem finished or doesn't have reports
                    if not has_reports:
                        JOBS[job_id]['status'] = 'failed'
                        JOBS[job_id]['output'] += '\n\nWARNING: No report files were generated.'
                        logging.warning(f'Job {job_id} has no reports but exited with code 0')
                    elif not is_garak_finished:
                        # Process exited but output doesn't indicate completion
                        JOBS[job_id]['status'] = 'running'  # Keep as running until frontend refreshes
                        logging.warning(f'Job {job_id} exited but output indicates it may still be running')
                
                # Save final job state to disk
                try:
                    with open(job_file_path, "w") as f:
                        json.dump(JOBS[job_id], f)
                except Exception as e:
                    logging.error(f"Failed to save final job state: {str(e)}")
                
                logging.info(f"Job {job_id} completed with status {JOBS[job_id]['status']}")
            
            except Exception as e:
                logging.error(f"Error in streaming thread for job {job_id}: {str(e)}")
                JOBS[job_id]['status'] = 'failed'
                JOBS[job_id]['output'] += f"\n\nERROR in output streaming: {str(e)}"
                JOBS[job_id]['end_time'] = datetime.now().isoformat()
                
                try:
                    with open(job_file_path, "w") as f:
                        json.dump(JOBS[job_id], f)
                except Exception as write_err:
                    logging.error(f"Failed to write error status: {str(write_err)}")
        
        # Start the output streaming in a background thread
        stream_thread = threading.Thread(target=stream_output)
        stream_thread.daemon = True
        stream_thread.start()
        
        return job_id
        
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
        
        return job_id

@app.route('/')
@auth.login_required
def index():
    """Main dashboard page"""
    return render_template('index.html', 
                           user_email=session.get('user_email', ''),
                           generators=GENERATORS, 
                           probe_categories=PROBE_CATEGORIES,
                           anthropic_models=ANTHROPIC_MODELS)

@app.route('/jobs')
@auth.login_required
def jobs():
    """View all jobs"""
    return render_template('jobs.html', user_email=session.get('user_email', ''), jobs=JOBS)

def reload_job_from_disk(job_id):
    """Reload a job from disk if it exists but is not in memory"""
    job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
    if os.path.exists(job_file_path):
        try:
            with open(job_file_path, 'r') as f:
                job_data = json.load(f)
            
            # Handle both 'id' and 'job_id' field names for compatibility
            if 'id' in job_data and 'job_id' not in job_data:
                job_data['job_id'] = job_data['id']
            elif 'job_id' in job_data and 'id' not in job_data:
                job_data['id'] = job_data['job_id']
            elif 'job_id' not in job_data and 'id' not in job_data:
                job_data['id'] = job_id
                job_data['job_id'] = job_id
                
            # Add the job to the in-memory dictionary
            JOBS[job_id] = job_data
            logging.info(f"Reloaded job {job_id} from disk")
            return True
        except Exception as e:
            logging.error(f"Error reloading job {job_id} from disk: {e}")
    return False

@app.route('/job/<job_id>')
@auth.login_required
def job_detail(job_id):
    """View job details"""
    # Try to reload the job from disk if it's not in memory
    if job_id not in JOBS and not reload_job_from_disk(job_id):
        return "Job not found", 404
    
    job = JOBS[job_id]
    
    # Parse report data for trust scores and failing prompts
    trust_score_data = {}
    failing_prompts = []
    json_report_path = None
    
    # Find the report JSON/JSONL file
    for ext in ['.report.jsonl', '.report.json']:
        potential_path = os.path.join(REPORT_DIR, f"{job_id}{ext}")
        if os.path.exists(potential_path):
            json_report_path = potential_path
            break
    
    if json_report_path:
        try:
            if json_report_path.endswith('.jsonl'):
                trust_score_data, failing_prompts = parse_jsonl_report(json_report_path)
            else:
                with open(json_report_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    # Process JSON report if needed
            # logging.info(f"Parsed report data for job {job_id} from {json_report_path}")
        except Exception as e:
            logging.error(f"Error parsing report data for job {job_id} from {json_report_path}: {e}")
    
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
    
    # Update stale output message for completed jobs
    if job.get('status') in ['completed', 'failed'] and job.get('output') == "Job is still running. Output will appear here when available.":
        if job.get('status') == 'completed':
            job['output'] = "Job completed successfully. No detailed output is available."
        else:
            job['output'] = "Job failed. No detailed error information is available."
        
        # Update job file on disk
        job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
        if os.path.exists(job_file_path):
            try:
                with open(job_file_path, 'r') as f:
                    job_config = json.load(f)
                job_config['output'] = job['output']
                with open(job_file_path, 'w') as f:
                    json.dump(job_config, f)
            except Exception as e:
                logging.error(f"Error updating output message in job file: {str(e)}")
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
    
    return render_template('job_detail.html', job=JOBS[job_id], job_id=job_id, 
                          html_report=html_report_content, trust_score_data=trust_score_data, 
                          failing_prompts=failing_prompts)

@app.route('/api/start_job', methods=['POST'])
@auth.login_required
def start_job():
    """API endpoint to start a new Garak job"""
    data = request.json
    generator = data.get('generator')
    model_name = data.get('model_name')
    selected_categories = data.get('categories', [])
    
    # Handle Anthropic models via LiteLLM
    if generator == 'anthropic' and model_name in ANTHROPIC_MODELS:
        generator = 'litellm'
        logging.info(f"Using LiteLLM for Anthropic model: {model_name}")
    api_keys = data.get('api_keys', {})
    parallel_attempts = data.get('parallel_attempts', 1)

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
    logging.info(f"Job {job_id}: Selected categories {selected_categories} expanded to {len(selected_probes)} probes.")

    # Create job entry
    JOBS[job_id] = {
        'id': job_id,
        'generator': generator,
        'model_name': model_name,
        'probes': selected_probes,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'api_keys': {k: '***' for k, v in api_keys.items() if v},  # Don't store actual keys in job history
        'parallel_attempts': parallel_attempts
    }

    # Start job in background thread
    thread = threading.Thread(
        target=run_garak_job,
        args=(job_id, generator, model_name, selected_probes, api_keys, parallel_attempts)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'status': 'success',
        'job_id': job_id,
        'message': f'Job started with ID: {job_id}'
    })

@app.route('/api/job_status/<job_id>')
@auth.login_required
def job_status(job_id):
    """Get status of a specific job"""
    if job_id not in JOBS:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404
    return jsonify({
        'status': 'success',
        'job': JOBS[job_id]
    })

@app.route('/api/job_progress/<job_id>')
@auth.login_required
def job_progress(job_id):
    """Get detailed progress information of a job, optimized for frequent polling"""
    if job_id not in JOBS:
        return jsonify({'status': 'error', 'message': 'Job not found'}), 404
        
    job = JOBS[job_id]
    
    # Calculate progress based on output lines for running jobs
    progress = 0
    completed_items = 0
    total_items = 100  # Default value
    
    # Check if the job is still running
    is_completed = job['status'] not in ['pending', 'running']
    
    # Calculate time metrics
    elapsed_time = ""
    time_remaining = ""
    estimated_completion = ""
    
    if 'start_time' in job:
        start_time = datetime.fromisoformat(job['start_time'])
        now = datetime.now()
        elapsed_seconds = (now - start_time).total_seconds()
        
        # Format elapsed time nicely
        elapsed_hours, remainder = divmod(elapsed_seconds, 3600)
        elapsed_minutes, elapsed_seconds = divmod(remainder, 60)
        elapsed_time = f"{int(elapsed_hours)}h {int(elapsed_minutes)}m {int(elapsed_seconds)}s"
        
        # Attempt to calculate progress from output
        if job['output']:
            # Look for progress indicators in the output
            output_lines = job['output'].split('\n')
            for line in output_lines:
                # Check for common progress indicators
                if "%" in line and any(x in line.lower() for x in ["progress", "complete", "done"]):
                    try:
                        # Extract percentage
                        percent_match = re.search(r'(\d+)%', line)
                        if percent_match:
                            progress = int(percent_match.group(1))
                    except:
                        pass
                        
                # Look for items processed patterns (e.g., "10 of 50 items processed")
                items_match = re.search(r'(\d+)\s+of\s+(\d+)', line)
                if items_match:
                    try:
                        completed_items = int(items_match.group(1))
                        total_items = int(items_match.group(2))
                        progress = int((completed_items / total_items) * 100)
                    except:
                        pass
                        
                # Look for tqdm progress bars which are common in Garak output
                tqdm_match = re.search(r'(\d+)%\|[\u2588\s]+\|\s+(\d+)/(\d+)', line)
                if tqdm_match:
                    try:
                        progress = int(tqdm_match.group(1))
                        completed_items = int(tqdm_match.group(2))
                        total_items = int(tqdm_match.group(3))
                    except:
                        pass
            
            # If we couldn't find explicit progress, estimate based on time
            if progress == 0 and 'end_time' not in job:
                # Make a very rough estimate based on common completion times
                # Typically garak jobs take 2-5 minutes depending on complexity
                estimated_total_seconds = 180  # 3 minutes is a common average
                
                # Adjust based on the probe count
                if 'probes' in job and isinstance(job['probes'], list):
                    estimated_total_seconds = 60 + (len(job['probes']) * 30)
                
                progress = min(95, int((elapsed_seconds / estimated_total_seconds) * 100))
                
                # Calculate estimated time remaining
                if progress > 0:
                    remaining_seconds = (elapsed_seconds / progress) * (100 - progress)
                    minutes, seconds = divmod(remaining_seconds, 60)
                    time_remaining = f"{int(minutes)}m {int(seconds)}s"
                    
                    completion_time = now + timedelta(seconds=remaining_seconds)
                    estimated_completion = completion_time.strftime('%H:%M:%S')
    
    # For completed jobs, set progress to 100%
    if is_completed:
        progress = 100
        time_remaining = "0s"
    
    return jsonify({
        'status': job['status'],
        'progress': progress,
        'completed': is_completed,
        'completed_items': completed_items,
        'total_items': total_items,
        'elapsed_time': elapsed_time,
        'time_remaining': time_remaining,
        'estimated_completion': estimated_completion,
        'output': job.get('output', '')
    })

@app.route('/download/<job_id>/<file_type>')
@auth.login_required
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

def parse_jsonl_report(report_path):
    """
    Parse a Garak JSONL report file and extract trust scores and failing prompts
    """
    trust_score_data = {}
    failing_prompts = []
    
    try:
        with jsonlines.open(report_path) as reader:
            for entry in reader:
                # Process configuration entries to get probe information
                if entry.get('entry_type') == 'start_run setup':
                    if 'plugins.probe_spec' in entry:
                        probe_specs = entry['plugins.probe_spec'].split(',')
                        for probe in probe_specs:
                            parts = probe.split('.')
                            if len(parts) == 2:
                                module, name = parts
                                if module not in trust_score_data:
                                    trust_score_data[module] = {'probes': {}}
                                if name not in trust_score_data[module]['probes']:
                                    trust_score_data[module]['probes'][name] = {
                                        'score': 100,  # Default to 100%
                                        'detectors': {}
                                    }
                
                # Process attempt entries to find failing prompts
                elif entry.get('entry_type') == 'attempt':
                    probe_name = entry.get('probe_classname', '')
                    detector_results = entry.get('detector_results', {})
                    prompt = entry.get('prompt', '')
                    outputs = entry.get('outputs', [])
                    goal = entry.get('goal', '')
                    
                    # Calculate if any detector found a problem (score of 0 indicates failure)
                    has_failures = False
                    for detector, scores in detector_results.items():
                        if any(score == 0.0 for score in scores):
                            has_failures = True
                            
                            # Update the detector score in trust_score_data
                            if probe_name:
                                parts = probe_name.split('.')
                                if len(parts) == 2:
                                    module, name = parts
                                    if module in trust_score_data and name in trust_score_data[module]['probes']:
                                        trust_score_data[module]['probes'][name]['score'] = min(
                                            trust_score_data[module]['probes'][name]['score'], 
                                            0  # Failed test
                                        )
                                        
                                        # Store detector info
                                        detector_name = detector.split('.')[-1] if '.' in detector else detector
                                        trust_score_data[module]['probes'][name]['detectors'][detector_name] = {
                                            'score': 0,
                                            'name': detector
                                        }
                    
                    # If this prompt caused a failure, add it to the list
                    if has_failures:
                        failing_entry = {
                            'probe': probe_name,
                            'prompt': prompt,
                            'output': outputs[0] if outputs else "No output",
                            'goal': goal,
                            'failing_detectors': []
                        }
                        
                        # Add which detectors failed
                        for detector, scores in detector_results.items():
                            if any(score == 0.0 for score in scores):
                                failing_entry['failing_detectors'].append(detector)
                        
                        failing_prompts.append(failing_entry)
        
        # Calculate module-level scores (average of probe scores)
        for module in trust_score_data:
            probe_scores = [probe['score'] for probe in trust_score_data[module]['probes'].values()]
            if probe_scores:
                trust_score_data[module]['score'] = sum(probe_scores) / len(probe_scores)
            else:
                trust_score_data[module]['score'] = 100
        
    except Exception as e:
        logging.error(f"Error parsing JSONL report: {e}")
    
    return trust_score_data, failing_prompts

# Register authentication routes
auth.register_auth_routes(app)

if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Garak Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    
    # Run the app
    debug_mode = os.environ.get('DEBUG', str(args.debug).lower()) == 'true'
    
    print(f"Starting Garak Dashboard on port {args.port} with debug={debug_mode}")
    app.run(host=args.host, port=args.port, debug=debug_mode)
