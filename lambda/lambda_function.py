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
    "exchange_rates/exchange_rates.csv.gz": "exchange_rate_stg",
    "company_overview/company_overview.csv.gz": "company_overview_stg",
    "daily_stock/daily_stock.csv.gz": "daily_stock_stg",
    "news_sentiment/news_sentiment.csv.gz": "news_sentiment_stg"
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


def get_table_columns(workgroup, database, table):
    sql = f"""
    SELECT "column"
    FROM pg_table_def
    WHERE schemaname = 'public'
      AND tablename = '{table}';
    """

    response = redshift.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql=sql
    )

    statement_id = response["Id"]
    result = wait_for_statement(statement_id)

    if result["Status"] != "FINISHED":
        print("Redshift error:", result)
        raise Exception("Failed to fetch table columns")

    records = redshift.get_statement_result(Id=statement_id)

    return [
        row[0]["stringValue"]
        for row in records["Records"]
    ]


def get_metadata_key(table):
    return f"metadata/{table}_metadata.csv"


def get_metadata_columns(bucket, table):
    metadata_key = get_metadata_key(table)

    print("Metadata key:", metadata_key)

    obj = s3.get_object(
        Bucket=bucket,
        Key=metadata_key
    )

    metadata_data = obj["Body"].read().decode("utf-8")

    reader = csv.DictReader(
        io.StringIO(metadata_data)
    )

    if "fieldname" not in reader.fieldnames:
        raise Exception(
            f"Metadata file {metadata_key} missing fieldname column"
        )

    metadata_columns = []

    for row in reader:
        fieldname = row["fieldname"].strip()

        if fieldname:
            metadata_columns.append(fieldname)

    if not metadata_columns:
        raise Exception(
            f"No metadata columns found in {metadata_key}"
        )

    return metadata_columns


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

    table_columns = get_table_columns(
        workgroup,
        database,
        table
    )

    metadata_columns = get_metadata_columns(
        bucket,
        table
    )

    print("File columns:", file_columns)
    print("Metadata columns:", metadata_columns)
    print("Table columns:", table_columns)

    if metadata_columns != table_columns:
        raise Exception(
            f"Metadata and table column mismatch. "
            f"Metadata columns: {metadata_columns}, "
            f"Table columns: {table_columns}"
        )

    if file_columns != metadata_columns:
        raise Exception(
            f"File and metadata column mismatch. "
            f"File columns: {file_columns}, "
            f"Metadata columns: {metadata_columns}"
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