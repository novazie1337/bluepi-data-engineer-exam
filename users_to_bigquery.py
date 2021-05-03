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
TABLE_NAME = os.environ.get("GCP_TABLE_NAME", 'users_to_bigquery')

dag = models.DAG(
    dag_id='airflow_gcs_to_bigquery_users',
    start_date=days_ago(1),
    schedule_interval=None,
    tags=['gcs_to_bigquery'],
)

create_users_dataset = BigQueryCreateEmptyDatasetOperator(
    task_id='users_dataset', dataset_id=DATASET_NAME, dag=dag
)

# [START howto_operator_gcs_to_bigquery]
load_users = GCSToBigQueryOperator(
    task_id='gcs_to_bigquery_users',
    bucket='airflow-postgres',
    source_objects=['users.csv'],
    destination_project_dataset_table=f"{DATASET_NAME}.{TABLE_NAME}",
    schema_fields=[
        {'name': 'created_at', 'type': 'DATE', 'mode': 'REQUIRED'},
        {'name': 'updated_at', 'type': 'DATE', 'mode': 'REQUIRED'},
        {'name': 'id', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'first_name', 'type': 'STRING', 'mode': 'REQUIRED'},
        {'name': 'last_name', 'type': 'STRING', 'mode': 'REQUIRED'},
    ],
    write_disposition='WRITE_TRUNCATE',
    dag=dag,
)
# [END howto_operator_gcs_to_bigquery]

delete_users_dataset = BigQueryDeleteDatasetOperator(
    task_id='delete_users_dataset', dataset_id=DATASET_NAME, delete_contents=True, dag=dag
)

create_users_dataset >> load_users >> delete_users_dataset