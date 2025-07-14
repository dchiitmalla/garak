import json
import os
import tempfile
from google.cloud import bigquery
from google.cloud import storage
from datetime import datetime

# Constants for GCP resources
PROJECT_ID = "garak-464900"
DATASET_ID = "garak"
REPORTS_TABLE_ID = "garak_reports_raw"
HITS_TABLE_ID = "garak_hitlog_raw"
BUCKET_NAME = "garak-dashboard-storage-garak-464900"

# Path to schema definitions relative to the function deployment
HITS_SCHEMA_PATH = "schemas/garak_hits_schema.json"
REPORTS_SCHEMA_PATH = "schemas/garak_reports_schema.json"

def load_schema(schema_path):
    """Load BigQuery schema from a JSON file."""
    with open(schema_path, 'r') as schema_file:
        return json.load(schema_file)

def create_table_if_not_exists(client, table_id, schema_path):
    """Creates a BigQuery table if it doesn't exist using the specified schema."""
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
    
    try:
        client.get_table(table_ref)
        print(f"Table {table_ref} already exists.")
    except Exception:
        # Table doesn't exist, create it
        schema = load_schema(schema_path)
        
        # Convert JSON schema to BigQuery schema objects
        bq_schema = []
        for field in schema:
            field_mode = field.get('mode', 'NULLABLE')
            field_schema = bigquery.SchemaField(
                field['name'], 
                field['type'], 
                mode=field_mode
            )
            bq_schema.append(field_schema)
        
        table = bigquery.Table(table_ref, schema=bq_schema)
        
        # Set clustering fields (using run_id as the primary key/join condition)
        table.clustering_fields = ["run_id"]
        
        table = client.create_table(table)
        print(f"Created table {table_ref}")
    
    return table_ref

def process_bucket_files():
    """Scan a GCS bucket and ingest Garak files."""
    credentials_path = "../../gcp-creds.json"
    try:
        storage_client = storage.Client.from_service_account_json(credentials_path)
        bigquery_client = bigquery.Client.from_service_account_json(credentials_path)
    except FileNotFoundError:
        error_msg = f"Service account file not found at '{credentials_path}'. Ensure it is in the root of the garak project."
        print(f"[ERROR] {error_msg}")
        return
    except Exception as e:
        error_msg = f"Failed to authenticate with service account: {e}"
        print(f"[ERROR] {error_msg}")
        return

    print("Successfully authenticated with service account.")

    # Ensure tables exist before processing
    reports_table_ref = create_table_if_not_exists(bigquery_client, REPORTS_TABLE_ID, REPORTS_SCHEMA_PATH)
    hits_table_ref = create_table_if_not_exists(bigquery_client, HITS_TABLE_ID, HITS_SCHEMA_PATH)

    bucket = storage_client.get_bucket(BUCKET_NAME)
    blobs = bucket.list_blobs()

    processed_count = 0
    for blob in blobs:
        # Skip files that have already been processed
        if blob.name.startswith('processed/'):
            continue

        # Process report files
        if blob.name.endswith(".report.jsonl"):
            print(f"Processing report file: {blob.name}")
            ingest_report_file(bigquery_client, reports_table_ref, blob)
            processed_count += 1

        # Process hitlog files
        elif blob.name.endswith(".hitlog.jsonl"):
            print(f"Processing hitlog file: {blob.name}")
            ingest_hitlog_file(bigquery_client, hits_table_ref, blob)
            processed_count += 1

        # Move the processed file to the 'processed' directory
        if blob.name.endswith(".jsonl"):
            processed_blob_name = f"processed/{blob.name}"
            bucket.rename_blob(blob, processed_blob_name)
            print(f"Moved {blob.name} to {processed_blob_name}")

    print(f"\nProcessed {processed_count} new files.")

def ingest_report_file(client, table_ref, blob):
    """Ingests a .report.jsonl file into BigQuery in batches."""
    table = client.get_table(table_ref)
    BATCH_SIZE = 500
    rows_to_insert = []
    total_inserted = 0

    with tempfile.NamedTemporaryFile(mode='wb+', delete=False) as temp_file:
        blob.download_to_file(temp_file)
        temp_file.close()

        def insert_batch(rows):
            if not rows:
                return 0
            errors = client.insert_rows_json(table, rows)
            if errors:
                print(f"Encountered errors while inserting rows into {table_ref}: {errors}")
                return 0
            print(f"Successfully inserted {len(rows)} rows into {table_ref}")
            return len(rows)

        run_id = None  # Track run_id for entries that don't have it
        with open(temp_file.name, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    row_json = json.loads(line)
                    entry_type = row_json.get('entry_type')
                    timestamp_str = None

                    if entry_type == "start_run setup":
                        run_id = row_json.get('transient.run_id')
                        timestamp_str = row_json.get('transient.starttime_iso')
                    elif entry_type == "init":
                        run_id = row_json.get('run')
                        timestamp_str = row_json.get('start_time')
                    elif entry_type == "completion":
                        run_id = row_json.get('run')
                        timestamp_str = row_json.get('end_time')

                    current_run_id = row_json.get('run') or run_id

                    row_to_insert = {
                        "entry_type": entry_type,
                        "timestamp": timestamp_str,
                        "run_id": current_run_id,
                        "json_payload": line.strip(),
                        "start_time": row_json.get('start_time'),
                        "end_time": row_json.get('end_time'),
                        "model_name": row_json.get('generator', {}).get('model_name', '') if isinstance(row_json.get('generator'), dict) else '',
                        "ingestion_time": datetime.utcnow().isoformat()
                    }
                    rows_to_insert.append(row_to_insert)

                    if len(rows_to_insert) >= BATCH_SIZE:
                        total_inserted += insert_batch(rows_to_insert)
                        rows_to_insert = []

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from line: {line.strip()} - {e}")

        # Insert any remaining rows
        if rows_to_insert:
            total_inserted += insert_batch(rows_to_insert)

        if total_inserted == 0:
            print(f"No new rows to insert from {blob.name}")
    
    os.remove(temp_file.name)

def ingest_hitlog_file(client, table_ref, blob):
    """Ingests a .hitlog.jsonl file into BigQuery in batches."""
    table = client.get_table(table_ref)
    BATCH_SIZE = 500
    rows_to_insert = []
    total_inserted = 0

    with tempfile.NamedTemporaryFile(mode='wb+', delete=False) as temp_file:
        blob.download_to_file(temp_file)
        temp_file.close()

        def insert_batch(rows):
            if not rows:
                return 0
            errors = client.insert_rows_json(table, rows)
            if errors:
                print(f"Encountered errors while inserting rows into {table_ref}: {errors}")
                return 0
            print(f"Successfully inserted {len(rows)} rows into {table_ref}")
            return len(rows)

        with open(temp_file.name, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    row = json.loads(line)

                    if 'triggers' not in row or row['triggers'] is None:
                        row['triggers'] = []
                    elif not isinstance(row['triggers'], list):
                        row['triggers'] = [row['triggers']]

                    row['ingestion_time'] = datetime.utcnow().isoformat()
                    rows_to_insert.append(row)

                    if len(rows_to_insert) >= BATCH_SIZE:
                        total_inserted += insert_batch(rows_to_insert)
                        rows_to_insert = []

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from line: {line.strip()} - {e}")

        # Insert any remaining rows
        if rows_to_insert:
            total_inserted += insert_batch(rows_to_insert)

        if total_inserted == 0:
            print(f"No new rows to insert from {blob.name}")
    
    os.remove(temp_file.name)

if __name__ == "__main__":
    process_bucket_files()
