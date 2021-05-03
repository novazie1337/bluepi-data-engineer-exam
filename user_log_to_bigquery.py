import os

from airflow import models
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateEmptyDatasetOperator,
    BigQueryDeleteDatasetOperator,
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

create_user_log_dataset = BigQueryCreateEmptyDatasetOperator(
    task_id='user_log_dataset', dataset_id=DATASET_NAME, dag=dag
)

# [START howto_operator_gcs_to_bigquery]
load_user_log = GCSToBigQueryOperator(
    task_id='gcs_to_bigquery_user_log',
    bucket='airflow-postgres',
    source_objects=['user_log.csv'],
    destination_project_dataset_table=f"{DATASET_NAME}.{TABLE_NAME}",
    schema_fields=[
        {'name': 'created_at', 'type': 'DATE', 'mode': 'REQUIRED'},
        {'name': 'updated_at', 'type': 'DATE', 'mode': 'REQUIRED'},
        {'name': 'id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'user_id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'action', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'success', 'type': 'BOOLEAN', 'mode': 'REQUIRED'},
    ],
    write_disposition='WRITE_TRUNCATE',
    dag=dag,
)
# [END howto_operator_gcs_to_bigquery]

delete_user_log_dataset = BigQueryDeleteDatasetOperator(
    task_id='delete_user_log_dataset', dataset_id=DATASET_NAME, delete_contents=True, dag=dag
)

create_user_log_dataset >> load_user_log >> delete_user_log_dataset