import boto3
import gzip
import csv
import os
import time
import json
import logging

s3 = boto3.client("s3")
redshift = boto3.client("redshift-data")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def wait_for_statement(statement_id):
    """
    Wait until a Redshift Data API statement reaches a final status.

    Purpose:
        Polls Redshift Data API until the SQL statement is FINISHED,
        FAILED, or ABORTED.

    Returns:
        dict: Final statement execution result.
    """
    while True:
        result = redshift.describe_statement(Id=statement_id)
        status = result["Status"]

        logger.info("Redshift statement id: %s", statement_id)
        logger.info("Redshift status: %s", status)

        if status in ["FINISHED", "FAILED", "ABORTED"]:
            return result

        time.sleep(1)


def execute_sql(workgroup, database, sql):
    """
    Execute SQL in Redshift Serverless.

    Purpose:
        Runs SQL using Redshift Data API and validates that the
        statement completes successfully.

    Returns:
        dict: Final Redshift statement result.
    """
    logger.info("Executing SQL: %s", sql)

    response = redshift.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql=sql
    )

    statement_id = response["Id"]
    result = wait_for_statement(statement_id)

    if result["Status"] != "FINISHED":
        logger.error("Redshift error result: %s", result)
        raise Exception("Redshift statement failed")

    return result


def get_statement_records(statement_id):
    """
    Retrieve all records from a Redshift Data API result set.

    Purpose:
        Handles paginated Redshift query results by reading all pages
        using NextToken.

    Returns:
        list: All records returned by the query.
    """
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
    """
    Extract a plain value from a Redshift Data API typed field.

    Purpose:
        Redshift Data API returns values with keys such as stringValue,
        longValue, doubleValue, booleanValue, and isNull. This method
        normalizes them into simple Python values.

    Returns:
        str | None: Extracted field value.
    """
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
    """
    Get ordered column names from a Redshift table.

    Purpose:
        Reads information_schema.columns to retrieve the Redshift table
        column list in ordinal position order. This is used for schema
        validation before loading data.

        Audit/pipeline-only columns (prefixed meta_, e.g. meta_loaded_at,
        meta_from_source) are excluded, since they are populated by
        Redshift defaults or by this Lambda after the COPY, and never
        appear in the source CSV or the metadata file.

    Returns:
        list: Ordered table column names, excluding meta_ audit columns.
    """
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
        logger.error("Failed to fetch table columns: %s", result)
        raise Exception("Failed to fetch table columns")

    records = get_statement_records(statement_id)

    table_columns = []

    for row in records:
        if row:
            value = extract_value(row[0])
            if value:
                table_columns.append(value)

    table_columns = [
        column for column in table_columns
        if not column.startswith("meta_")
    ]

    return table_columns


def get_schema_mapping(bucket, s3_key):
    """
    Read target schema and table mapping from S3 metadata file.

    Purpose:
        Keeps S3 key to Redshift schema/table mapping outside Lambda code.
        This allows new datasets to be onboarded by updating
        metadata_schema_mapping.csv instead of redeploying Lambda.

    Returns:
        dict: Target schema and table information.
    """
    mapping_key = "metadata/table_mapping/metadata_schema_mapping.csv"

    logger.info("Schema mapping key: %s", mapping_key)

    obj = s3.get_object(
        Bucket=bucket,
        Key=mapping_key
    )

    mapping_data = obj["Body"].read().decode("utf-8-sig")

    reader = csv.DictReader(
        mapping_data.splitlines()
    )

    required_columns = {
        "s3_key",
        "schema_name",
        "table_name"
    }

    if not reader.fieldnames or not required_columns.issubset(
        reader.fieldnames
    ):
        raise Exception(
            f"Schema mapping file {mapping_key} missing required columns"
        )

    for row in reader:
        if row["s3_key"].strip() == s3_key:
            return {
                "schema": row["schema_name"].strip(),
                "table": row["table_name"].strip()
            }

    raise Exception(
        f"No schema mapping found for {s3_key}"
    )


def get_metadata_key(table):
    """
    Build metadata file key for a Redshift table.

    Purpose:
        Returns the S3 key for the table-level metadata file.

    Returns:
        str: S3 metadata file key.
    """
    return f"metadata/{table}_metadata.csv"


def get_metadata_columns(bucket, table):
    """
    Read expected column names from table metadata CSV in S3.

    Purpose:
        Extracts the ordered fieldname list from the metadata file.
        The result is compared against the CSV header and Redshift
        table column list.

    Returns:
        list: Ordered metadata column names.
    """
    metadata_key = get_metadata_key(table)

    logger.info("Metadata key: %s", metadata_key)

    obj = s3.get_object(
        Bucket=bucket,
        Key=metadata_key
    )

    metadata_data = obj["Body"].read().decode("utf-8-sig")

    reader = csv.DictReader(
        metadata_data.splitlines()
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


def get_csv_header_columns(bucket, s3_key):
    """
    Read only the header row from a gzip-compressed CSV file in S3.

    Purpose:
        Avoids loading the full CSV.GZ file into Lambda memory. This
        allows large datasets to be validated safely before Redshift COPY.

    Returns:
        list: Ordered CSV header columns.
    """
    obj = s3.get_object(
        Bucket=bucket,
        Key=s3_key
    )

    with gzip.GzipFile(fileobj=obj["Body"]) as gz:
        header_line = gz.readline().decode("utf-8-sig").strip()

    logger.info("CSV header line: %s", header_line)

    reader = csv.reader([header_line])
    return next(reader)


def get_s3_key_from_event(event):
    """
    Extract S3 object key from an SNS-wrapped S3 event.

    Purpose:
        The Lambda is triggered by SNS. The original S3 event is inside
        the SNS message as a JSON string. This method parses it and
        returns the uploaded object key.

    Returns:
        str: Uploaded S3 object key.
    """
    sns_message = event["Records"][0]["Sns"]["Message"]
    s3_event = json.loads(sns_message)

    return s3_event["Records"][0]["s3"]["object"]["key"]


def copy_to_redshift(event, context):
    """
    Validate an uploaded CSV.GZ file and load it into Redshift.

    Purpose:
        Handles the complete ingestion process:
        - extract S3 key from SNS event
        - skip metadata files
        - resolve target schema/table from metadata_schema_mapping.csv
        - validate CSV header against metadata and Redshift table columns
        - load data into Redshift using COPY, with an explicit column
          list so audit-only columns (e.g. meta_loaded_at) can carry
          their own DEFAULT (e.g. GETDATE()) without needing to be
          present in the source CSV
        - stamp the loaded rows with meta_from_source, recording the
          full S3 path the data was loaded from

    Returns:
        dict: Lambda response with load status.
    """
    try:
        logger.info("Lambda triggered")
        logger.info("Lambda version: meta_from_source support")

        bucket = os.environ["BUCKET"]
        workgroup = os.environ["WORKGROUP"]
        database = os.environ["DATABASE"]

        logger.info("Env BUCKET: %s", bucket)
        logger.info("Env WORKGROUP: %s", workgroup)
        logger.info("Env DATABASE: %s", database)

        s3_key = get_s3_key_from_event(event)

        logger.info("Triggered S3 key: %s", s3_key)

        if s3_key.startswith("metadata/"):
            logger.info("Skipping metadata file: %s", s3_key)
            return {
                "statusCode": 200,
                "body": f"Skipped metadata file: {s3_key}"
            }

        mapping = get_schema_mapping(
            bucket,
            s3_key
        )

        schema = mapping["schema"]
        table = mapping["table"]

        logger.info("Target schema: %s", schema)
        logger.info("Target table: %s", table)

        file_columns = get_csv_header_columns(
            bucket,
            s3_key
        )

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

        logger.info("File columns: %s", file_columns)
        logger.info("Metadata columns: %s", metadata_columns)
        logger.info("Table columns (excluding meta_ audit columns): %s", table_columns)

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

        column_list = ", ".join(metadata_columns)

        copy_sql = f"""
        TRUNCATE TABLE {schema}.{table};

        COPY {schema}.{table}
        ({column_list})
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

        logger.info("Copied file into %s.%s", schema, table)

        s3_source_path = f"s3://{bucket}/{s3_key}"

        update_sql = f"""
        UPDATE {schema}.{table}
        SET meta_from_source = '{s3_source_path}'
        WHERE meta_from_source IS NULL;
        """

        execute_sql(
            workgroup,
            database,
            update_sql
        )

        logger.info(
            "Set meta_from_source to %s for %s.%s",
            s3_source_path,
            schema,
            table
        )

        return {
            "statusCode": 200,
            "body": f"Copied file into {schema}.{table}"
        }

    except Exception:
        logger.exception("Lambda failed during S3 to Redshift load")
        raise


def lambda_handler(event, context):
    """
    Lambda entry point.

    Purpose:
        Delegates the SNS-triggered ingestion event to copy_to_redshift.

    Returns:
        dict: Lambda response.
    """
    return copy_to_redshift(event, context)