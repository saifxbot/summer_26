import boto3
import gzip
import csv
import io
import os
import time
import json

s3 = boto3.client("s3")
redshift = boto3.client("redshift-data")


TABLE_MAPPING = {
    "real_gdp/real_gdp.csv.gz": "gdp_stg",
    "exchange_rates/exchange_rates.csv.gz": "exchange_rate_stg"
}


EXPECTED_COLUMNS = {
    "gdp_stg": [
        "date",
        "value"
    ],
    "exchange_rate_stg": [
        "rate_date",
        "from_currency",
        "to_currency",
        "exchange_rate"
    ]
}


def wait_for_statement(statement_id):
    while True:
        result = redshift.describe_statement(Id=statement_id)
        status = result["Status"]

        print("Redshift status:", status)

        if status in ["FINISHED", "FAILED", "ABORTED"]:
            return result

        time.sleep(1)


def execute_sql(workgroup, database, sql):
    response = redshift.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql=sql
    )

    statement_id = response["Id"]
    print("Redshift statement id:", statement_id)

    result = wait_for_statement(statement_id)

    if result["Status"] != "FINISHED":
        print("Redshift error:", result)
        raise Exception("Redshift statement failed")

    return result


def get_table_columns(table):
    if table not in EXPECTED_COLUMNS:
        raise Exception(f"No column mapping found for {table}")

    return EXPECTED_COLUMNS[table]


def get_s3_key_from_event(event):
    sns_message = event["Records"][0]["Sns"]["Message"]
    s3_event = json.loads(sns_message)

    return s3_event["Records"][0]["s3"]["object"]["key"]


def copy_to_redshift(event, context):
    print("Lambda triggered")

    bucket = os.environ["BUCKET"]
    workgroup = os.environ["WORKGROUP"]
    database = os.environ["DATABASE"]

    s3_key = get_s3_key_from_event(event)

    print("Triggered S3 key:", s3_key)

    if s3_key not in TABLE_MAPPING:
        raise Exception(
            f"No staging table mapping found for {s3_key}"
        )

    table = TABLE_MAPPING[s3_key]

    obj = s3.get_object(
        Bucket=bucket,
        Key=s3_key
    )

    compressed = obj["Body"].read()

    csv_data = gzip.decompress(
        compressed
    ).decode("utf-8")

    reader = csv.DictReader(
        io.StringIO(csv_data)
    )

    file_columns = reader.fieldnames

    table_columns = get_table_columns(table)

    print("File columns:", file_columns)
    print("Table columns:", table_columns)

    if file_columns != table_columns:
        raise Exception(
            f"Column mismatch. File columns: {file_columns}, Table columns: {table_columns}"
        )

    rows = list(reader)

    if not rows:
        raise Exception("No rows found in file")

    values = []

    for row in rows:
        row_values = []

        for column in file_columns:
            value = row[column]

            if value == "":
                row_values.append("NULL")
            else:
                escaped_value = value.replace("'", "''")
                row_values.append(
                    f"'{escaped_value}'"
                )

        values.append(
            f"({','.join(row_values)})"
        )

    column_names = ",".join(file_columns)

    sql = f"""
    TRUNCATE TABLE public.{table};

    INSERT INTO public.{table} ({column_names})
    VALUES {",".join(values)};
    """

    execute_sql(
        workgroup,
        database,
        sql
    )

    print(
        f"Inserted {len(rows)} rows into public.{table}"
    )

    return {
        "statusCode": 200,
        "body": f"Inserted {len(rows)} rows into public.{table}"
    }


def lambda_handler(event, context):
    return copy_to_redshift(event, context)