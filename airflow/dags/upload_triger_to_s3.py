from datetime import datetime
import boto3

from airflow import DAG
from airflow.operators.python import PythonOperator


BUCKET_NAME = "summer-26-project"
TRIGGER_FILE_KEY = "airflow-trigger/trigger.txt"


def upload_trigger_file():
    s3 = boto3.client("s3", region_name="eu-west-1")

    content = "Triggered by local Airflow DAG"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=TRIGGER_FILE_KEY,
        Body=content.encode("utf-8"),
    )

    print(f"Uploaded trigger file to s3://{BUCKET_NAME}/{TRIGGER_FILE_KEY}")


with DAG(
    dag_id="upload_trigger_to_s3",
    start_date=datetime(2026, 6, 1),
    schedule=None,
    catchup=False,
    tags=["s3", "sns", "lambda"],
) as dag:

    upload_file_task = PythonOperator(
        task_id="upload_trigger_file",
        python_callable=upload_trigger_file,
    )