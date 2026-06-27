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
    "real_gdp/real_gdp.csv.gz": {
        "schema": "public",
        "table": "gdp_stg"
    },
    "exchange_rates/exchange_rates.csv.gz": {
        "schema": "public",
        "table": "exchange_rate_stg"
    },
    "company_overview/company_overview.csv.gz": {
        "schema": "public",
        "table": "company_overview_stg"
    },
    "daily_stock/daily_stock.csv.gz": {
        "schema": "public",
        "table": "daily_stock_stg"
    },
    "news_sentiment/news_sentiment.csv.gz": {
        "schema": "public",
        "table": "news_sentiment_stg"
    },
    "operating_cash_balance/operating_cash_balance.csv.gz": {
        "schema": "source_fiscaldata",
        "table": "operating_cash_balance_stg"
    }
}


def wait_for_statement(statement_id):
    while True:
        result = redshift.describe_statement(Id=statement_id)
        status = result["Status"]

        print("Redshift statement id:", statement_id)
        print("Redshift status:", status)

        if status in ["FINISHED", "FAILED", "ABORTED"]:
            return result

        time.sleep(1)


def execute_sql(workgroup, database, sql):
    print("Executing SQL:")
    print(sql)

    response = redshift.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql=sql
    )

    statement_id = response["Id"]
    result = wait_for_statement(statement_id)

    if result["Status"] != "FINISHED":
        print("Redshift error result:")
        print(result)
        raise Exception("Redshift statement failed")

    return result


def get_statement_records(statement_id):
    records = []
    next_token = None

    while True:
        if next_token:
            response = redshift.get_statement_result(
                Id=statement_id,
                NextToken=next_token
            )
        else:
            response = redshift.get_statement_result(
                Id=statement_id
            )

        records.extend(response.get("Records", []))
        next_token = response.get("NextToken")

        if not next_token:
            break

    return records


def extract_value(field):
    if "stringValue" in field:
        return field["stringValue"]

    if "longValue" in field:
        return str(field["longValue"])

    if "doubleValue" in field:
        return str(field["doubleValue"])

    if "booleanValue" in field:
        return str(field["booleanValue"])

    if field.get("isNull"):
        return None

    return str(field)


def get_table_columns(workgroup, database, schema, table):
    print("Fetching table columns")
    print("Workgroup:", workgroup)
    print("Database:", database)
    print("Schema:", schema)
    print("Table:", table)

    sql = f"""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = '{schema}'
      AND table_name = '{table}'
    ORDER BY ordinal_position;
    """

    response = redshift.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql=sql
    )

    statement_id = response["Id"]
    result = wait_for_statement(statement_id)

    if result["Status"] != "FINISHED":
        print("Redshift error:")
        print(result)
        raise Exception("Failed to fetch table columns")

    records = get_statement_records(statement_id)

    table_columns = []

    for row in records:
        if row:
            value = extract_value(row[0])
            if value:
                table_columns.append(value)

    print("Table columns:", table_columns)

    return table_columns


def get_metadata_key(table):
    return f"metadata/{table}_metadata.csv"


def get_metadata_columns(bucket, table):
    metadata_key = get_metadata_key(table)

    print("Metadata key:", metadata_key)

    obj = s3.get_object(
        Bucket=bucket,
        Key=metadata_key
    )

    metadata_data = obj["Body"].read().decode("utf-8-sig")

    reader = csv.DictReader(
        io.StringIO(metadata_data)
    )

    if not reader.fieldnames or "fieldname" not in reader.fieldnames:
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
    print("Lambda version: schema-aware copy load")

    bucket = os.environ["BUCKET"]
    workgroup = os.environ["WORKGROUP"]
    database = os.environ["DATABASE"]

    print("Env BUCKET:", bucket)
    print("Env WORKGROUP:", workgroup)
    print("Env DATABASE:", database)

    s3_key = get_s3_key_from_event(event)

    print("Triggered S3 key:", s3_key)

    if s3_key.startswith("metadata/"):
        print(f"Skipping metadata file: {s3_key}")
        return {
            "statusCode": 200,
            "body": f"Skipped metadata file: {s3_key}"
        }

    if s3_key not in TABLE_MAPPING:
        raise Exception(
            f"No staging table mapping found for {s3_key}"
        )

    mapping = TABLE_MAPPING[s3_key]
    schema = mapping["schema"]
    table = mapping["table"]

    print("Target schema:", schema)
    print("Target table:", table)

    obj = s3.get_object(
        Bucket=bucket,
        Key=s3_key
    )

    compressed = obj["Body"].read()

    csv_data = gzip.decompress(
        compressed
    ).decode("utf-8-sig")

    reader = csv.DictReader(
        io.StringIO(csv_data)
    )

    file_columns = reader.fieldnames

    if not file_columns:
        raise Exception("CSV file has no header columns")

    table_columns = get_table_columns(
        workgroup,
        database,
        schema,
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

    copy_sql = f"""
    TRUNCATE TABLE {schema}.{table};

    COPY {schema}.{table}
    FROM 's3://{bucket}/{s3_key}'
    IAM_ROLE default
    FORMAT AS CSV
    IGNOREHEADER 1
    GZIP
    EMPTYASNULL
    BLANKSASNULL;
    """

    execute_sql(
        workgroup,
        database,
        copy_sql
    )

    print(f"Copied file into {schema}.{table}")

    return {
        "statusCode": 200,
        "body": f"Copied file into {schema}.{table}"
    }


def lambda_handler(event, context):
    return copy_to_redshift(event, context)