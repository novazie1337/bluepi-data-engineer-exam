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
TABLE_NAME = os.environ.get("GCP_TABLE_NAME", 'users_to_bigquery')

dag = models.DAG(
    dag_id='airflow_gcs_to_bigquery_users',
    start_date=days_ago(1),
    schedule_interval=None,
    tags=['gcs_to_bigquery'],
)

def users_converter():
    json_gcs = []
    
    gcs_file_system = gcsfs.GCSFileSystem(project="sirapob-bluepi-de-exam", token="cloud")
    gcs_json_path = "gs://airflow-postgres/users"
    with gcs_file_system.open(gcs_json_path) as f:
        gcs_string_data = json.loads(json.dumps(f.read().decode('utf-8')))
        gcs = gcs_string_data.splitlines()
        for g in gcs:
            gcs = json.loads(g) 
            gcs['created_at'] = dt.datetime.fromtimestamp(gcs['created_at']) + dt.timedelta(hours=7)
            gcs['updated_at'] = dt.datetime.fromtimestamp(gcs['updated_at']) + dt.timedelta(hours=7)
            json_gcs.append(gcs)

    storage_client = storage.Client()
    bucket = storage_client.get_bucket("airflow-postgres")
    blob = bucket.blob("users.csv")
    df = pd.DataFrame(data=json_gcs).to_csv(sep=",", header=False, index=False, quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8')
    blob.upload_from_string(data=df)

create_users_dataset = BigQueryCreateEmptyDatasetOperator(
    task_id='users_dataset', dataset_id=DATASET_NAME, dag=dag
)

convert_input_file = PythonOperator(
    task_id='convert_users',
    python_callable=users_converter,
    dag=dag
)

load_users = GCSToBigQueryOperator(
    task_id='gcs_to_bigquery_users',
    bucket='airflow-postgres',
    source_objects=['users.csv'],
    destination_project_dataset_table=f"{DATASET_NAME}.{TABLE_NAME}",
    schema_fields=[
        {'name': 'created_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
        {'name': 'first_name', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'last_name', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'updated_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
    ],
    write_disposition='WRITE_TRUNCATE',
    source_format='CSV',
    encoding='UTF-8',
    dag=dag,
)

create_users_dataset >> convert_input_file >> load_users