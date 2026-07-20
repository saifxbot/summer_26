import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


ENV = os.getenv("ENV", "dev")

default_args = {
    "owner": "saif",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="redshift_loads_fiscaldata",
    description="Run stg-to-main Redshift load procedures for all fiscaldata tables",
    default_args=default_args,
    start_date=datetime(2026, 6, 1),
    schedule="@daily",
    catchup=False,
    tags=["redshift", "fiscaldata", "load"],
) as dag:

    incr_source_fiscaldata_operating_cash_balance = SQLExecuteQueryOperator(
        task_id="incr_source_fiscaldata_operating_cash_balance",
        conn_id="redshift_wdp_" + ENV,
        autocommit=True,
        sql="sql/incr_source_fiscaldata_operating_cash_balance.sql",
    )

    incr_source_fiscaldata_deposits_withdrawals_operating_cash = SQLExecuteQueryOperator(
        task_id="incr_source_fiscaldata_deposits_withdrawals_operating_cash",
        conn_id="redshift_wdp_" + ENV,
        autocommit=True,
        sql="sql/incr_source_fiscaldata_deposits_withdrawals_operating_cash.sql",
    )

    incr_source_fiscaldata_treasury_reporting_rates_exchange = SQLExecuteQueryOperator(
        task_id="incr_source_fiscaldata_treasury_reporting_rates_exchange",
        conn_id="redshift_wdp_" + ENV,
        autocommit=True,
        sql="sql/incr_source_fiscaldata_treasury_reporting_rates_exchange.sql",
    )