from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import os
import json
import uuid
import threading
import subprocess
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'garak-dashboard-secret-key')

# Store running jobs
JOBS = {}

# Load existing jobs from disk
def load_existing_jobs():
    job_count = 0
    try:
        # List all job files in the data directory
        for filename in os.listdir(DATA_DIR):
            if filename.startswith('job_') and filename.endswith('.json'):
                job_path = os.path.join(DATA_DIR, filename)
                try:
                    with open(job_path, 'r') as f:
                        job_data = json.load(f)
                        if 'job_id' in job_data:
                            job_id = job_data['job_id']
                            JOBS[job_id] = job_data
                            # Check if report files exist for this job
                            report_prefix = job_data.get('report_prefix', '')
                            report_json_path = f"{report_prefix}.report.json"
                            report_jsonl_path = f"{report_prefix}.report.jsonl"
                            if os.path.exists(report_json_path):
                                JOBS[job_id]['report_path'] = report_json_path
                            if os.path.exists(report_jsonl_path):
                                JOBS[job_id]['hits_path'] = report_jsonl_path
                            job_count += 1
                except Exception as e:
                    logging.error(f"Error loading job file {filename}: {str(e)}")
        logging.info(f"Loaded {job_count} existing jobs from disk")
    except Exception as e:
        logging.error(f"Error loading existing jobs: {str(e)}")

# Don't load jobs yet - DATA_DIR not defined yet

# Configuration
REPORT_DIR = os.environ.get('REPORT_DIR', '/app/reports')
DATA_DIR = os.environ.get('DATA_DIR', '/app/data')
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Now load existing jobs after directories are defined
load_existing_jobs()

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
    """Run a Garak job directly using Garak CLI"""
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
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Save job config for reference
        job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
        with open(job_file_path, 'w') as f:
            json.dump(job_config, f)
            
        logging.info(f"Created job file: {job_file_path}")
        
        # Update job status to running
        JOBS[job_id]['status'] = 'running'
        JOBS[job_id]['start_time'] = datetime.now().isoformat()
        
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
        report_prefix = f"/app/reports/{job_id}"
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
        stdout_path = f"/app/reports/{job_id}_stdout.log"
        stderr_path = f"/app/reports/{job_id}_stderr.log"
        
        with open(stdout_path, "wb") as f:
            f.write(stdout)
            
        with open(stderr_path, "wb") as f:
            f.write(stderr)
        
        # Set report file paths
        report_json_path = f"{report_prefix}.report.json"
        report_jsonl_path = f"{report_prefix}.report.jsonl"
        
        # Update job status and report paths
        JOBS[job_id]['status'] = 'completed' if return_code == 0 else 'failed'
        JOBS[job_id]['output'] = stdout.decode('utf-8', errors='replace') if stdout else ''
        JOBS[job_id]['error'] = stderr.decode('utf-8', errors='replace') if stderr else ''
        JOBS[job_id]['end_time'] = datetime.now().isoformat()
        JOBS[job_id]['return_code'] = return_code
        
        # Update job file with current status
        job_config['status'] = JOBS[job_id]['status']
        job_config['end_time'] = JOBS[job_id]['end_time']
        job_config['return_code'] = return_code
        
        # Write updated job status to disk
        with open(job_file_path, 'w') as f:
            json.dump(job_config, f)
            
        logging.info(f"Job {job_id} completed with status {job_config['status']}")
        
        JOBS[job_id]['report_path'] = report_json_path
        JOBS[job_id]['hits_path'] = report_jsonl_path
        
        logging.info(f"Job {job_id} completed with status {JOBS[job_id]['status']}")
        return JOBS[job_id]
        
    except Exception as e:
        logging.error(f"Error in job {job_id}: {str(e)}")
        JOBS[job_id]['status'] = 'failed'
        JOBS[job_id]['output'] = str(e)
        JOBS[job_id]['end_time'] = datetime.now().isoformat()
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
    
    # Handle older jobs that don't have output field but have report files
    if 'output' not in job and job.get('status') == 'completed':
        # Check if the report exists
        report_jsonl_path = f"{job.get('report_prefix', os.path.join(REPORT_DIR, job_id))}.report.jsonl"
        
        if os.path.exists(report_jsonl_path):
            # Add the hits path if it doesn't exist
            if 'hits_path' not in job:
                job['hits_path'] = report_jsonl_path
                
            # Add a default output showing the report was generated successfully
            job['output'] = f"Garak scan completed successfully. Report available at: {report_jsonl_path}\n\nTo view report contents, download using the buttons on the left."
        else:
            job['output'] = "No output logs available for this job."
    
    return render_template('job_detail.html', job=JOBS[job_id], job_id=job_id)

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
    if job_id not in JOBS or JOBS[job_id]['status'] != 'completed':
        return "Report not available", 404
    
    if file_type == 'report':
        file_path = JOBS[job_id]['report_path']
        filename = f"garak_report_{job_id}.json"
    elif file_type == 'hits':
        file_path = JOBS[job_id]['hits_path']
        filename = f"garak_hits_{job_id}.jsonl"
    else:
        return "Invalid file type", 400
    
    if not os.path.exists(file_path):
        return "File not found", 404
    
    return send_file(file_path, as_attachment=True, download_name=filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
