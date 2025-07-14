import argparse
import json
import re
import os
import datetime
from bs4 import BeautifulSoup

# Import optional dependency
try:
    from google.cloud import bigquery
    from google.cloud import storage
except ImportError:
    bigquery = None
    storage = None

def extract_metadata(soup):
    """Extracts top-level metadata from the report header."""
    metadata = {}
    
    # First, try to get UUID from the title
    title = soup.find('title')
    if title:
        title_text = title.text.strip()
        match = re.search(r'garak report: (.*?).report.jsonl', title_text)
        if match:
            metadata['run_uuid'] = match.group(1).strip()

    # Find the config details section
    config_header = soup.find('h2', string='config details')
    if config_header and config_header.find_next_sibling('pre'):
        pre_text = config_header.find_next_sibling('pre').get_text()
        
        # Extract garak version
        version_match = re.search(r'garak version: (.*)', pre_text)
        if version_match:
            metadata['garak_version'] = version_match.group(1).strip()

        # Extract model name (target generator)
        model_match = re.search(r'target generator: (.*)', pre_text)
        if model_match:
            metadata['model_name'] = model_match.group(1).strip()

        # Extract start time
        time_match = re.search(r'run started at: (.*)', pre_text)
        if time_match:
            metadata['start_time'] = time_match.group(1).strip()
            
        # If run_uuid wasn't in title, try to get it from filename
        if 'run_uuid' not in metadata:
            filename_match = re.search(r'filename: (.*?).report.jsonl', pre_text)
            if filename_match:
                metadata['run_uuid'] = filename_match.group(1).strip()

    # Set defaults for any fields that were not found
    metadata.setdefault('run_uuid', None)
    metadata.setdefault('model_name', None)
    metadata.setdefault('garak_version', None)
    metadata.setdefault('start_time', None)

    return metadata

def parse_html_report(html_content):
    """Parses the HTML content of a Garak report and extracts structured data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    report_metadata = extract_metadata(soup)
    records = []

    probe_groups = soup.find_all('div', class_='panel')

    for group in probe_groups:
        group_button = group.find_previous_sibling('button', class_='accordion')
        if not group_button or not group_button.find('b'):
            continue
        group_name = group_button.find('b').text.strip()

        current_probe_name = None
        current_probe_descr = None

        for element in group.find_all(['h3', 'h4'], recursive=False):
            if element.name == 'h3':
                probe_text = element.text.strip()
                match = re.search(r'probe: (.*?) - min. (.*?)%', probe_text)
                if match:
                    current_probe_name = match.group(1).strip()
                    current_probe_descr = element.get('title', '').strip()

            elif element.name == 'h4' and current_probe_name:
                detector_name = element.find('p', class_='left').text.replace('detector:', '').strip()
                detector_descr = element.get('title', '').strip()
                score_divs = element.find_next_siblings('div', class_='detector score', limit=2)
                
                pass_rate = 0.0
                absolute_score_str = None
                z_score = None
                absolute_defcon = None
                relative_defcon = None

                # Placeholders for schema alignment
                passed_count = None
                total_count = None

                if score_divs and len(score_divs) > 0:
                    # Extract absolute score
                    absolute_score_b = score_divs[0].find('b')
                    if absolute_score_b:
                        absolute_score_text = absolute_score_b.text.strip()
                        absolute_score_str = absolute_score_text
                        pass_rate_match = re.search(r'(\d+\.\d+|\d+)', absolute_score_text)
                        if pass_rate_match:
                            pass_rate = float(pass_rate_match.group(1))

                    # Extract absolute defcon
                    defcon_span = score_divs[0].find('span', class_='dc')
                    if defcon_span:
                        defcon_text = defcon_span.text.strip()
                        defcon_match = re.search(r'DC:(\d+)', defcon_text)
                        if defcon_match:
                            absolute_defcon = int(defcon_match.group(1))

                    # Extract relative score and defcon
                    if len(score_divs) > 1:
                        relative_score_b = score_divs[1].find('b')
                        if relative_score_b:
                            relative_score_text = relative_score_b.text.strip()
                            z_match = re.search(r'(-?\d+\.\d+|-?\d+)', relative_score_text)
                            if z_match:
                                z_score = float(z_match.group(1))
                        
                        defcon_span = score_divs[1].find('span', class_='dc')
                        if defcon_span:
                            defcon_text = defcon_span.text.strip()
                            defcon_match = re.search(r'DC:(\d+)', defcon_text)
                            if defcon_match:
                                relative_defcon = int(defcon_match.group(1))

                defcon_match = re.search(r'defcon(\d)', ' '.join(element.get('class', [])))
                final_defcon = int(defcon_match.group(1)) if defcon_match else None

                records.append({
                    'probe_group': group_name,
                    'probe_name': current_probe_name,
                    'probe_description': current_probe_descr,
                    'detector_name': detector_name,
                    'detector_description': detector_descr,
                    'pass_rate': pass_rate,
                    'absolute_score': absolute_score_str, # Will be dropped in BQ upload
                    'z_score': z_score,
                    'final_defcon': final_defcon,
                    # Add placeholders
                    'passed_count': passed_count,
                    'total_count': total_count,
                    'absolute_defcon': absolute_defcon,
                    'relative_defcon': relative_defcon
                })

    return report_metadata, records

def upload_to_bigquery(records, bigquery_client, project_id, dataset_id, table_id):
    """Uploads a list of processed records to a BigQuery table."""
    if not bigquery:
        raise ImportError("google-cloud-bigquery library is required for upload. Please run 'pip install google-cloud-bigquery'.")

    table_ref = bigquery_client.dataset(dataset_id).table(table_id)

    rows_to_insert = []
    for record in records:
        # Map and enrich the data to match the BigQuery schema
        row = {
            'run_uuid': record.get('run_uuid'),
            'model_name': record.get('model_name'),
            'start_time': record.get('start_time'),
            'garak_version': record.get('garak_version'),
            'probe_group': record.get('probe_group'),
            'probe_module': record.get('probe_name', '').split('.')[0],
            'probe_class': record.get('probe_name'),
            'probe_descr': record.get('probe_description'),
            'detector_module': record.get('detector_name', '').split('.')[0],
            'detector_class': record.get('detector_name'),
            'detector_descr': record.get('detector_description'),
            'pass_rate': record.get('pass_rate'),
            'absolute_defcon': record.get('absolute_defcon'),
            'z_score': record.get('z_score'),
            'relative_defcon': record.get('relative_defcon'),
            'final_defcon': record.get('final_defcon'),
            'load_timestamp': datetime.datetime.utcnow().isoformat(),
            # Add other missing fields with None
            'model_type': None,
            'probe_tags': None,
            'probe_tier': None,
            'passed_count': record.get('passed_count'),
            'total_count': record.get('total_count'),
            'taxonomy_used': None
        }
        rows_to_insert.append(row)

    if not rows_to_insert:
        print("No records to upload.")
        return

    errors = bigquery_client.insert_rows_json(table_ref, rows_to_insert)
    if not errors:
        print(f"Successfully uploaded {len(rows_to_insert)} records to {project_id}.{dataset_id}.{table_id}")
    else:
        print("Encountered errors while inserting rows:")
        for error in errors:
            print(error)

def move_blob_to_processed(bucket, blob):
    """Moves a blob to the 'processed/' directory in the same bucket."""
    processed_folder = 'processed/'
    # Ensure the destination blob name is unique to avoid overwriting
    destination_blob_name = f"{processed_folder}{blob.name}"

    print(f"    -> Moving to {destination_blob_name}")
    
    # Copy the blob to the new location
    bucket.copy_blob(blob, bucket, destination_blob_name)

    # Delete the original blob
    blob.delete()

    print(f"    -> Move complete.")

def process_gcs_to_bigquery(move_files=False):
    """Processes all HTML reports in a GCS bucket and uploads results to BigQuery."""
    # --- Configuration ---
    project_id = "garak-464900"
    bucket_name = "garak-dashboard-storage-garak-464900"
    dataset_id = "garak"
    table_id = "garak_scan_results"
    credentials_path = "../gcp-creds.json"

    # --- Check for Libraries ---
    if not storage or not bigquery:
        raise ImportError("GCP libraries required. Please run 'pip install google-cloud-storage google-cloud-bigquery'.")

    # --- Initialize Clients from Service Account ---
    try:
        storage_client = storage.Client.from_service_account_json(credentials_path)
        bigquery_client = bigquery.Client.from_service_account_json(credentials_path)
    except FileNotFoundError:
        print(f"[ERROR] Service account file not found at '{credentials_path}'.")
        print("Please ensure the credentials file is in the root of the garak project.")
        return
    except Exception as e:
        print(f"[ERROR] Failed to authenticate with service account: {e}")
        return

    print(f"Authenticated with '{credentials_path}'.")
    print(f"Scanning bucket 'gs://{bucket_name}' for reports...")

    # --- Process Files from GCS ---
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    all_records = []

    # Convert iterator to list to avoid issues with modification during iteration
    blob_list = list(blobs)

    for blob in blob_list:
        if blob.name.startswith('processed/'):
            continue

        if blob.name.endswith('.html'):
            print(f"  - Processing {blob.name}...")
            try:
                html_content = blob.download_as_text()
                report_metadata, records = parse_html_report(html_content)
                
                # Combine metadata with each record
                for record in records:
                    combined_record = report_metadata.copy()
                    combined_record.update(record)
                    all_records.append(combined_record)

                print(f"    ...found {len(records)} records.")

                # If processing was successful and move_files is True, move the blob
                if move_files:
                    move_blob_to_processed(bucket, blob)

            except Exception as e:
                print(f"    [ERROR] Failed to process {blob.name}: {e}")

    # --- Upload to BigQuery ---
    if all_records:
        print(f"\nUploading {len(all_records)} total records to BigQuery...")
        upload_to_bigquery(all_records, bigquery_client, project_id, dataset_id, table_id)
    else:
        print("No reports found or processed. Nothing to upload.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Garak HTML reports from GCS and upload to BigQuery.')
    parser.add_argument(
        '--move-processed-files',
        action='store_true',
        help='Move processed HTML files to a `processed/` directory in the GCS bucket.'
    )
    args = parser.parse_args()

    process_gcs_to_bigquery(move_files=args.move_processed_files)
