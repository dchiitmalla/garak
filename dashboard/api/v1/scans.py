"""
Garak Dashboard Public API v1 endpoints.

This module provides the public REST API for interacting with garak
red-teaming scans programmatically.
"""

import os
import uuid
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app, send_file, g
from pydantic import ValidationError

# Import our custom modules
from api.core.auth import api_key_required, read_required, write_required
from api.core.rate_limiter import rate_limit
from api.core.models import (
    CreateScanRequest, UpdateScanRequest, ScanResponse, ScanListResponse,
    ScanMetadata, ScanResult, ReportInfo, ReportType, ScanStatus,
    ErrorResponse, GeneratorInfo, ProbeCategory, ProbeInfo,
    scan_to_metadata
)
from api.core.utils import (
    get_jobs_data, get_probe_categories, get_generators, get_anthropic_models,
    run_garak_job_wrapper, validate_json_request, create_error_handler
)

# Blueprint for API v1
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


# Utility functions are now imported from api.core.utils


@api_v1.errorhandler(Exception)
def handle_api_error(error):
    """Global error handler for API v1."""
    return create_error_handler("API v1")(error)


# Scan Management Endpoints

@api_v1.route('/scans', methods=['POST'])
@write_required
@rate_limit(limit=10, window=60)  # 10 scans per minute
@validate_json_request(CreateScanRequest)
def create_scan(request_data: CreateScanRequest):
    """Create a new garak security scan."""
    try:
        # Generate unique scan ID
        scan_id = str(uuid.uuid4())
        
        # Get probe categories and expand to individual probes
        probe_categories_map = get_probe_categories()
        selected_probes = []
        
        if request_data.probes:
            # Use explicitly specified probes
            selected_probes = request_data.probes
        else:
            # Expand categories to individual probes
            for category in request_data.probe_categories:
                if category in probe_categories_map:
                    selected_probes.extend(probe_categories_map[category])
        
        if not selected_probes:
            return jsonify(ErrorResponse(
                error="no_probes_selected",
                message="No probes specified. Provide either 'probes' or 'probe_categories'"
            ).model_dump()), 400
        
        # Handle Anthropic models via LiteLLM
        generator = request_data.generator
        model_name = request_data.model_name
        if generator == 'anthropic' and model_name in get_anthropic_models():
            generator = 'litellm'
            current_app.logger.info(f"Using LiteLLM for Anthropic model: {model_name}")
        
        # Create job entry
        jobs_data = get_jobs_data()
        job_data = {
            'id': scan_id,
            'job_id': scan_id,  # For backward compatibility
            'name': request_data.name,
            'description': request_data.description,
            'generator': generator,
            'model_name': model_name,
            'probe_categories': request_data.probe_categories,
            'probes': selected_probes,
            'status': ScanStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'parallel_attempts': request_data.parallel_attempts,
            'api_keys': {k: '***' for k, v in request_data.api_keys.items() if v},  # Mask keys
            'created_by_api': True,
            'api_key_id': g.api_key_info['id']
        }
        
        jobs_data[scan_id] = job_data
        
        # Also update the global JOBS dictionary for compatibility with run_garak_job
        from app import JOBS
        JOBS[scan_id] = job_data.copy()
        
        # Ensure job is persisted to disk before starting execution
        from app import DATA_DIR
        import json
        import tempfile
        
        job_file_path = os.path.join(DATA_DIR, f"job_{scan_id}.json")
        temp_path = job_file_path + '.tmp'
        try:
            # Use atomic write to prevent race conditions
            with open(temp_path, 'w') as f:
                json.dump(job_data, f, indent=2)
                f.flush()  # Ensure data is written
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic move to final location
            os.rename(temp_path, job_file_path)
            current_app.logger.info(f"Job {scan_id} persisted to disk: {job_file_path}")
        except Exception as e:
            current_app.logger.error(f"Failed to persist job {scan_id} to disk: {e}")
            # Clean up temp file if it exists
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            return jsonify(ErrorResponse(
                error="scan_persistence_failed",
                message="Failed to save scan to disk"
            ).model_dump()), 500
        
        # Start job in background thread
        thread = threading.Thread(
            target=run_garak_job_wrapper,
            args=(scan_id, generator, model_name, selected_probes, 
                  request_data.api_keys, request_data.parallel_attempts, request_data.rest_config)
        )
        thread.daemon = True
        thread.start()
        
        # Return scan metadata
        metadata = scan_to_metadata(job_data)
        
        current_app.logger.info(
            f"Created scan {scan_id} via API - "
            f"Key: {g.api_key_info['key_prefix']} ({g.api_key_info['name']})"
        )
        
        return jsonify({
            'scan_id': scan_id,
            'message': f'Scan created successfully with ID: {scan_id}',
            'metadata': metadata.model_dump()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating scan: {str(e)}")
        return jsonify(ErrorResponse(
            error="scan_creation_failed",
            message=f"Failed to create scan: {str(e)}"
        ).model_dump()), 500


@api_v1.route('/scans', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def list_scans():
    """List all scans with pagination."""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 per page
        status_filter = request.args.get('status')
        
        jobs_data = get_jobs_data()
        
        # Ensure jobs are loaded from disk if not in memory
        if not jobs_data:
            current_app.logger.info("Jobs data empty, attempting to reload from disk")
            _reload_jobs_from_disk()
            jobs_data = get_jobs_data()
        
        # Filter scans by status if specified
        scans = []
        for job_id, job_data in jobs_data.items():
            try:
                if status_filter and job_data.get('status') != status_filter:
                    continue
                scans.append(scan_to_metadata(job_data))
            except Exception as e:
                current_app.logger.warning(f"Failed to process job {job_id}: {e}")
                continue
        
        # Sort by creation date (most recent first)
        scans.sort(key=lambda x: x.created_at, reverse=True)
        
        # Paginate
        total = len(scans)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_scans = scans[start_idx:end_idx]
        
        response = ScanListResponse(
            scans=page_scans,
            total=total,
            page=page,
            per_page=per_page,
            has_next=end_idx < total
        )
        
        return jsonify(response.model_dump())
        
    except Exception as e:
        current_app.logger.error(f"Error listing scans: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(
            error="scan_list_failed",
            message="Failed to retrieve scan list"
        ).model_dump()), 500


@api_v1.route('/scans/<scan_id>', methods=['GET'])
@read_required
@rate_limit(limit=200, window=60)
def get_scan(scan_id: str):
    """Get detailed information about a specific scan."""
    try:
        jobs_data = get_jobs_data()
        
        # If scan not found in memory, try to reload from disk
        if scan_id not in jobs_data:
            current_app.logger.info(f"Scan {scan_id} not found in memory, attempting to reload from disk")
            if _reload_specific_job(scan_id):
                jobs_data = get_jobs_data()
            else:
                return jsonify(ErrorResponse(
                    error="scan_not_found",
                    message=f"Scan with ID {scan_id} not found"
                ).model_dump()), 404
        
        job_data = jobs_data[scan_id]
        
        # Build scan response
        metadata = scan_to_metadata(job_data)
        
        # Get results if scan is completed
        results = None
        if job_data.get('status') == ScanStatus.COMPLETED.value:
            results = _extract_scan_results(job_data)
        
        # Get available reports
        reports = _get_available_reports(scan_id, job_data)
        
        # Get output log
        output_log = job_data.get('output', '')
        
        response = ScanResponse(
            metadata=metadata,
            results=results,
            reports=reports,
            output_log=output_log
        )
        
        return jsonify(response.model_dump())
        
    except Exception as e:
        current_app.logger.error(f"Error getting scan {scan_id}: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(
            error="scan_retrieval_failed",
            message="Failed to retrieve scan information"
        ).model_dump()), 500


@api_v1.route('/scans/<scan_id>/status', methods=['GET'])
@read_required
@rate_limit(limit=300, window=60)  # Higher limit for status checks
def get_scan_status(scan_id: str):
    """Get the current status of a scan (lightweight endpoint)."""
    try:
        jobs_data = get_jobs_data()
        
        # If scan not found in memory, try to reload from disk
        if scan_id not in jobs_data:
            current_app.logger.info(f"Scan {scan_id} not found in memory for status check, attempting to reload from disk")
            if not _reload_specific_job(scan_id):
                return jsonify(ErrorResponse(
                    error="scan_not_found",
                    message=f"Scan with ID {scan_id} not found"
                ).model_dump()), 404
            jobs_data = get_jobs_data()
        
        job_data = jobs_data[scan_id]
        metadata = scan_to_metadata(job_data)
        
        return jsonify({
            'scan_id': scan_id,
            'status': metadata.status,
            'progress': metadata.progress.model_dump() if metadata.progress else None,
            'created_at': metadata.created_at.isoformat(),
            'started_at': metadata.started_at.isoformat() if metadata.started_at else None,
            'completed_at': metadata.completed_at.isoformat() if metadata.completed_at else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting scan status {scan_id}: {str(e)}", exc_info=True)
        return jsonify(ErrorResponse(
            error="status_retrieval_failed",
            message="Failed to retrieve scan status"
        ).model_dump()), 500


@api_v1.route('/scans/<scan_id>/progress', methods=['GET'])
@read_required
@rate_limit(limit=500, window=60)  # High limit for progress polling
def get_scan_progress(scan_id: str):
    """Get detailed progress information for a running scan."""
    try:
        jobs_data = get_jobs_data()
        
        if scan_id not in jobs_data:
            return jsonify(ErrorResponse(
                error="scan_not_found",
                message=f"Scan with ID {scan_id} not found"
            ).model_dump()), 404
        
        job_data = jobs_data[scan_id]
        
        # Use the existing progress logic from main app
        from app import job_progress
        
        # Temporarily set job_id in the job data if not present
        if 'job_id' not in job_data:
            job_data['job_id'] = scan_id
            
        # Create a mock Flask request context for the existing function
        with current_app.test_request_context():
            # Call the existing progress function logic
            progress_response = _get_progress_data(job_data)
            
        return jsonify(progress_response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting scan progress {scan_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="progress_retrieval_failed",
            message="Failed to retrieve scan progress"
        ).model_dump()), 500


@api_v1.route('/scans/<scan_id>', methods=['PATCH'])
@write_required
@rate_limit(limit=50, window=60)
@validate_json_request(UpdateScanRequest)
def update_scan(request_data: UpdateScanRequest, scan_id: str):
    """Update scan metadata (name, description)."""
    try:
        jobs_data = get_jobs_data()
        
        if scan_id not in jobs_data:
            return jsonify(ErrorResponse(
                error="scan_not_found",
                message=f"Scan with ID {scan_id} not found"
            ).model_dump()), 404
        
        job_data = jobs_data[scan_id]
        
        # Update fields if provided
        if request_data.name is not None:
            job_data['name'] = request_data.name
        if request_data.description is not None:
            job_data['description'] = request_data.description
        
        # Save to disk
        from app import DATA_DIR
        job_file_path = os.path.join(DATA_DIR, f"job_{scan_id}.json")
        import json
        try:
            with open(job_file_path, 'w') as f:
                json.dump(job_data, f)
        except Exception as e:
            current_app.logger.warning(f"Failed to update job file: {e}")
        
        metadata = scan_to_metadata(job_data)
        
        return jsonify({
            'message': 'Scan updated successfully',
            'metadata': metadata.model_dump()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating scan {scan_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="scan_update_failed",
            message="Failed to update scan"
        ).model_dump()), 500


@api_v1.route('/scans/<scan_id>', methods=['DELETE'])
@write_required
@rate_limit(limit=20, window=60)
def cancel_scan(scan_id: str):
    """Cancel a running scan."""
    try:
        jobs_data = get_jobs_data()
        
        if scan_id not in jobs_data:
            return jsonify(ErrorResponse(
                error="scan_not_found",
                message=f"Scan with ID {scan_id} not found"
            ).model_dump()), 404
        
        job_data = jobs_data[scan_id]
        
        # Only allow cancelling pending or running scans
        if job_data.get('status') not in [ScanStatus.PENDING.value, ScanStatus.RUNNING.value]:
            return jsonify(ErrorResponse(
                error="scan_not_cancellable",
                message=f"Cannot cancel scan with status: {job_data.get('status')}"
            ).model_dump()), 400
        
        # Update status to cancelled
        job_data['status'] = ScanStatus.CANCELLED.value
        job_data['end_time'] = datetime.now().isoformat()
        
        # TODO: Implement actual process termination if scan is running
        # This would require tracking process IDs and terminating them
        
        # Save to disk
        from app import DATA_DIR
        job_file_path = os.path.join(DATA_DIR, f"job_{scan_id}.json")
        import json
        try:
            with open(job_file_path, 'w') as f:
                json.dump(job_data, f)
        except Exception as e:
            current_app.logger.warning(f"Failed to update job file: {e}")
        
        current_app.logger.info(f"Cancelled scan {scan_id} via API")
        
        return jsonify({
            'message': f'Scan {scan_id} has been cancelled',
            'status': ScanStatus.CANCELLED.value
        })
        
    except Exception as e:
        current_app.logger.error(f"Error cancelling scan {scan_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="scan_cancellation_failed",
            message="Failed to cancel scan"
        ).model_dump()), 500


# Report Download Endpoints

@api_v1.route('/scans/<scan_id>/reports', methods=['GET'])
@read_required
@rate_limit(limit=100, window=60)
def list_scan_reports(scan_id: str):
    """List available reports for a scan."""
    try:
        jobs_data = get_jobs_data()
        
        if scan_id not in jobs_data:
            return jsonify(ErrorResponse(
                error="scan_not_found",
                message=f"Scan with ID {scan_id} not found"
            ).model_dump()), 404
        
        job_data = jobs_data[scan_id]
        reports = _get_available_reports(scan_id, job_data)
        
        return jsonify({
            'scan_id': scan_id,
            'reports': [report.model_dump() for report in reports]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing reports for scan {scan_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="report_list_failed",
            message="Failed to list scan reports"
        ).model_dump()), 500


@api_v1.route('/scans/<scan_id>/reports/<report_type>', methods=['GET'])
@read_required
@rate_limit(limit=50, window=60)
def download_scan_report(scan_id: str, report_type: str):
    """Download a specific report file."""
    try:
        jobs_data = get_jobs_data()
        
        if scan_id not in jobs_data:
            return jsonify(ErrorResponse(
                error="scan_not_found",
                message=f"Scan with ID {scan_id} not found"
            ).model_dump()), 404
        
        # Validate report type
        if report_type not in [rt.value for rt in ReportType]:
            return jsonify(ErrorResponse(
                error="invalid_report_type",
                message=f"Invalid report type: {report_type}. Valid types: {[rt.value for rt in ReportType]}"
            ).model_dump()), 400
        
        job_data = jobs_data[scan_id]
        
        # Find the report file
        from app import REPORT_DIR
        file_path = None
        filename = None
        
        if report_type == ReportType.JSON.value:
            file_path = job_data.get('report_path') or os.path.join(REPORT_DIR, f"{scan_id}.report.json")
            filename = f"garak_report_{scan_id}.json"
        elif report_type == ReportType.JSONL.value:
            file_path = job_data.get('hits_path') or os.path.join(REPORT_DIR, f"{scan_id}.report.jsonl")
            filename = f"garak_report_{scan_id}.jsonl"
        elif report_type == ReportType.HTML.value:
            file_path = os.path.join(REPORT_DIR, f"{scan_id}.report.html")
            filename = f"garak_report_{scan_id}.html"
        elif report_type == ReportType.HITS.value:
            file_path = os.path.join(REPORT_DIR, f"{scan_id}.hitlog.jsonl")
            filename = f"garak_hits_{scan_id}.jsonl"
        
        if not file_path or not os.path.exists(file_path):
            return jsonify(ErrorResponse(
                error="report_not_found",
                message=f"Report file not found: {report_type}"
            ).model_dump()), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        current_app.logger.error(f"Error downloading report {report_type} for scan {scan_id}: {str(e)}")
        return jsonify(ErrorResponse(
            error="report_download_failed",
            message="Failed to download report"
        ).model_dump()), 500


# Helper Functions

def _reload_jobs_from_disk():
    """Reload all jobs from disk into memory."""
    try:
        from app import load_existing_jobs
        load_existing_jobs()
        current_app.logger.info("Successfully reloaded jobs from disk")
    except Exception as e:
        current_app.logger.error(f"Failed to reload jobs from disk: {e}")


def _reload_specific_job(job_id: str) -> bool:
    """Reload a specific job from disk into memory."""
    try:
        from app import DATA_DIR
        import json
        
        job_file_path = os.path.join(DATA_DIR, f"job_{job_id}.json")
        if not os.path.exists(job_file_path):
            current_app.logger.warning(f"Job file not found for {job_id}")
            return False
        
        # Check if file is empty or too small to contain valid JSON
        if os.path.getsize(job_file_path) == 0:
            current_app.logger.warning(f"Job file for {job_id} is empty")
            return False
        
        with open(job_file_path, 'r') as f:
            content = f.read().strip()
            if not content:
                current_app.logger.warning(f"Job file for {job_id} contains only whitespace")
                return False
                
            job_data = json.loads(content)
        
        # Ensure job_data is a dictionary and has required fields
        if not isinstance(job_data, dict):
            current_app.logger.warning(f"Job file for {job_id} does not contain a valid job object")
            return False
            
        # Ensure it has at least the job_id field
        if 'job_id' not in job_data and 'id' not in job_data:
            current_app.logger.warning(f"Job file for {job_id} missing required ID field")
            return False
        
        # Update the global JOBS dictionary
        jobs_data = get_jobs_data()
        jobs_data[job_id] = job_data
        
        current_app.logger.info(f"Successfully reloaded job {job_id} from disk")
        return True
        
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Failed to parse JSON for job {job_id}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to reload job {job_id} from disk: {e}")
        return False


def _get_progress_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract progress data from job information."""
    # This replicates logic from the existing job_progress function
    progress = 0
    completed_items = 0
    total_items = 100
    
    is_completed = job_data['status'] not in ['pending', 'running']
    
    elapsed_time = ""
    time_remaining = ""
    estimated_completion = ""
    
    if 'start_time' in job_data:
        start_time = datetime.fromisoformat(job_data['start_time'])
        now = datetime.now()
        elapsed_seconds = (now - start_time).total_seconds()
        
        elapsed_hours, remainder = divmod(elapsed_seconds, 3600)
        elapsed_minutes, elapsed_seconds = divmod(remainder, 60)
        elapsed_time = f"{int(elapsed_hours)}h {int(elapsed_minutes)}m {int(elapsed_seconds)}s"
        
        # Simple progress estimation
        if not is_completed:
            if 'probes' in job_data and isinstance(job_data['probes'], list):
                estimated_total_seconds = 60 + (len(job_data['probes']) * 30)
                progress = min(95, int((elapsed_seconds / estimated_total_seconds) * 100))
    
    if is_completed:
        progress = 100
        time_remaining = "0s"
    
    return {
        'status': job_data['status'],
        'progress': progress,
        'completed': is_completed,
        'completed_items': completed_items,
        'total_items': total_items,
        'elapsed_time': elapsed_time,
        'time_remaining': time_remaining,
        'estimated_completion': estimated_completion,
        'output': job_data.get('output', '')
    }


def _extract_scan_results(job_data: Dict[str, Any]) -> Optional[ScanResult]:
    """Extract scan results from completed job data."""
    try:
        # Basic result extraction - this could be enhanced with actual report parsing
        probes = job_data.get('probes', [])
        total_probes = len(probes)
        
        # Placeholder values - these would come from actual report parsing
        return ScanResult(
            total_probes=total_probes,
            total_attempts=total_probes * job_data.get('parallel_attempts', 1),
            failed_attempts=0,  # Would need to parse from reports
            success_rate=100.0,  # Would need to parse from reports
            trust_scores={},  # Would need to parse from reports
            key_findings=[]  # Would need to parse from reports
        )
        
    except Exception as e:
        current_app.logger.error(f"Error extracting scan results: {e}")
        return None


def _get_available_reports(scan_id: str, job_data: Dict[str, Any]) -> List[ReportInfo]:
    """Get list of available report files for a scan."""
    from app import REPORT_DIR
    reports = []
    
    report_files = [
        (ReportType.JSON, f"{scan_id}.report.json"),
        (ReportType.JSONL, f"{scan_id}.report.jsonl"),
        (ReportType.HTML, f"{scan_id}.report.html"),
        (ReportType.HITS, f"{scan_id}.hitlog.jsonl")
    ]
    
    for report_type, filename in report_files:
        file_path = os.path.join(REPORT_DIR, filename)
        if os.path.exists(file_path):
            try:
                stat = os.stat(file_path)
                reports.append(ReportInfo(
                    type=report_type,
                    file_path=file_path,
                    file_size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime),
                    download_url=f"/api/v1/scans/{scan_id}/reports/{report_type.value}"
                ))
            except Exception as e:
                current_app.logger.warning(f"Error getting file info for {file_path}: {e}")
    
    return reports