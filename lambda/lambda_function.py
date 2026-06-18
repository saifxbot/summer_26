import boto3
import gzip
import csv
import io
import os
import time

s3 = boto3.client("s3")
redshift = boto3.client("redshift-data")


def wait_for_statement(statement_id):
    while True:
        result = redshift.describe_statement(Id=statement_id)
        status = result["Status"]

        print("Redshift status:", status)

        if status in ["FINISHED", "FAILED", "ABORTED"]:
            return result

        time.sleep(1)


def copy_to_redshift(event, context):
    print("Lambda triggered")

    bucket = os.environ["BUCKET"]
    key = os.environ["KEY"]
    workgroup = os.environ["WORKGROUP"]
    database = os.environ["DATABASE"]
    table = os.environ["TABLE"]

    obj = s3.get_object(Bucket=bucket, Key=key)
    compressed = obj["Body"].read()
    csv_data = gzip.decompress(compressed).decode("utf-8")

    reader = csv.DictReader(io.StringIO(csv_data))

    values = []
    for row in reader:
        values.append(f"('{row['date']}', {row['value']})")

    sql = f"""
    TRUNCATE TABLE public.{table};

    INSERT INTO public.{table}
    VALUES {",".join(values)};
    """

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

    print(f"Inserted {len(values)} rows into public.{table}")

    return {
        "statusCode": 200,
        "body": f"Inserted {len(values)} rows into public.{table}"
    }