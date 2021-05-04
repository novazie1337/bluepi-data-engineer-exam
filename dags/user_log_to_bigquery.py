import os
import gcsfs
import json
import csv
import pandas as pd
import datetime as dt

from google.cloud import storage

from airflow import models
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateEmptyDatasetOperator
)
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.utils.dates import days_ago
from airflow.operators.python_operator import PythonOperator

DATASET_NAME = os.environ.get("GCP_DATASET_NAME", 'airflow_gcs_to_bigquery')
TABLE_NAME = os.environ.get("GCP_TABLE_NAME", 'user_log_to_bigquery')

dag = models.DAG(
    dag_id='airflow_gcs_to_bigquery_user_log',
    start_date=days_ago(1),
    schedule_interval=None,
    tags=['gcs_to_bigquery'],
)

def user_log_converter():
    json_gcs = []
    
    gcs_file_system = gcsfs.GCSFileSystem(project="sirapob-bluepi-de-exam", token="cloud")
    gcs_json_path = "gs://airflow-postgres/user_log"
    with gcs_file_system.open(gcs_json_path) as f:
        gcs_string_data = json.loads(json.dumps(f.read().decode('utf-8')))
        gcs = gcs_string_data.splitlines()
        for g in gcs:
            gcs = json.loads(g)
            gcs['created_at'] = dt.datetime.fromtimestamp(gcs['created_at']) + dt.timedelta(hours=7)
            gcs['updated_at'] = dt.datetime.fromtimestamp(gcs['updated_at']) + dt.timedelta(hours=7)
            gcs['status'] = True if gcs['status'] == 1 else False
            json_gcs.append(gcs)

    storage_client = storage.Client()
    bucket = storage_client.get_bucket("airflow-postgres")
    blob = bucket.blob("user_log.csv")
    df = pd.DataFrame(data=json_gcs).to_csv(sep=",", header=False, index=False, quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8')
    blob.upload_from_string(data=df)

create_user_log_dataset = BigQueryCreateEmptyDatasetOperator(
    task_id='user_log_dataset', dataset_id=DATASET_NAME, dag=dag
)

convert_input_file = PythonOperator(
    task_id='convert_user_log',
    python_callable=user_log_converter,
    dag=dag
)

load_user_log = GCSToBigQueryOperator(
    task_id='gcs_to_bigquery_user_log',
    bucket='airflow-postgres',
    source_objects=['user_log.csv'],
    destination_project_dataset_table=f"{DATASET_NAME}.{TABLE_NAME}",
    schema_fields=[
        {'name': 'action', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'created_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'success', 'type': 'BOOLEAN', 'mode': 'REQUIRED'},
        {'name': 'updated_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'user_id', 'type': 'STRING', 'mode': 'REQUIRED'}
    ],
    write_disposition='WRITE_TRUNCATE',
    source_format='CSV',
    encoding='UTF-8',
    dag=dag,
)

create_user_log_dataset >> convert_input_file >> load_user_log