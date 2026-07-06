import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator


AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
ECS_CLUSTER = os.getenv("ECS_CLUSTER")
ECS_SUBNET_ID = os.getenv("ECS_SUBNET_ID")
ECS_SECURITY_GROUP_ID = os.getenv("ECS_SECURITY_GROUP_ID")

ECS_TASK_DEFINITION = "deposits-withdrawals-operating-cash-task"


default_args = {
    "owner": "saif",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="deposits_withdrawals_operating_cash_fargate_task",
    description="Run Treasury deposits and withdrawals of operating cash extraction Fargate task daily and upload CSV gzip to S3",
    default_args=default_args,
    start_date=datetime(2026, 6, 1),
    schedule="@daily",
    catchup=False,
    tags=["aws", "ecs", "fargate", "fiscaldata", "deposits-withdrawals"],
) as dag:

    run_deposits_withdrawals_operating_cash_fargate_task = EcsRunTaskOperator(
        task_id="run_deposits_withdrawals_operating_cash_fargate_task",
        cluster=ECS_CLUSTER,
        task_definition=ECS_TASK_DEFINITION,
        launch_type="FARGATE",
        region_name=AWS_REGION,
        overrides={},
        network_configuration={
            "awsvpcConfiguration": {
                "subnets": [ECS_SUBNET_ID],
                "securityGroups": [ECS_SECURITY_GROUP_ID],
                "assignPublicIp": "ENABLED",
            }
        },
        awslogs_group="/ecs/deposits-withdrawals-operating-cash",
        awslogs_region=AWS_REGION,
        awslogs_stream_prefix="ecs",
    )