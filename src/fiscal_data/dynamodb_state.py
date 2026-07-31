import configparser
import logging
import os
import tempfile
from datetime import datetime, timezone
from io import BytesIO

import boto3
import pandas as pd
from botocore.exceptions import ClientError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)

_LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, "settings.ini")
    config.read(config_path)
    return config


def _get_state_table():
    config = load_config()
    region = config.get("aws", "region")
    table_name = config.get("dynamodb", "state_table")
    return boto3.resource("dynamodb", region_name=region).Table(table_name)


def get_watermark(dataset):
    """
    Read the last fetched record_date for a dataset from DynamoDB.

    Purpose:
        Returns the watermark (inclusive lower bound) used to build the
        API filter=record_date:gte:<watermark>. A missing item means this
        dataset has never been fetched incrementally, so the caller falls
        back to a full load (no filter).

    Returns:
        str | None: Last record_date as YYYY-MM-DD, or None if absent.
    """
    table = _get_state_table()

    response = table.get_item(
        Key={"dataset": dataset}
    )

    item = response.get("Item")

    if not item:
        return None

    return item.get("last_record_date")


def set_watermark(dataset, last_record_date, record_count):
    """
    Persist the new watermark for a dataset into DynamoDB.

    Purpose:
        UpdateItem has upsert semantics, so a missing item is created and
        the whole update is a single atomic write (no read-then-write race
        on the watermark item).

    Returns:
        None
    """
    table = _get_state_table()

    table.update_item(
        Key={"dataset": dataset},
        UpdateExpression=(
            "SET last_record_date = :d, "
            "record_count = :c, "
            "last_run_at = :t"
        ),
        ExpressionAttributeValues={
            ":d": last_record_date,
            ":c": int(record_count),
            ":t": datetime.now(timezone.utc).isoformat(),
        },
    )

    _LOGGER.info(
        "Watermark updated for %s: %s (%s rows)",
        dataset,
        last_record_date,
        record_count
    )


# Natural business keys used to dedupe merged rows. These match the
# Redshift PRIMARY KEY and the keyflag=X columns in the stg metadata.
NATURAL_KEYS = {
    "operating_cash_balance": ["record_date", "account_type", "src_line_nbr"],
    "deposits_withdrawals_operating_cash": ["record_date", "transaction_type", "src_line_nbr"],
    "treasury_reporting_rates_exchange": ["record_date", "country", "currency", "src_line_nbr"],
}


def _download_existing(bucket, s3_key, columns, region):
    """
    Download and parse the existing dataset CSV.GZ from S3.

    Purpose:
        Reads the previous full dataset so new rows can be merged into it.
        A missing object (first run) returns None instead of raising.

    Returns:
        pd.DataFrame | None: Existing rows as strings, or None if the
        object does not exist yet.
    """
    s3 = boto3.client("s3", region_name=region)

    try:
        obj = s3.get_object(Bucket=bucket, Key=s3_key)
    except ClientError as error:
        if error.response["Error"]["Code"] == "NoSuchKey":
            _LOGGER.info("No existing file at s3://%s/%s; first run", bucket, s3_key)
            return None

        raise

    df = pd.read_csv(
        BytesIO(obj["Body"].read()),
        compression="gzip",
        dtype=str,
        keep_default_na=False
    )

    # Force canonical column order so the merged CSV always matches the
    # stg metadata order (and therefore the Redshift column list).
    return df.reindex(columns=columns)


def frames_equivalent(left, right):
    """
    Compare two DataFrames by value, ignoring dtype differences.

    Purpose:
        The existing CSV is read back with string dtypes while newly
        fetched rows carry object dtypes. A bare df.equals would report
        False even when every value is identical, so both frames are
        normalized to strings before comparing.

    Returns:
        bool: True when both frames hold identical values.
    """
    if left.shape != right.shape:
        return False

    left_norm = left.fillna("").astype(str)
    right_norm = right.fillna("").astype(str)

    return (left_norm.to_numpy() == right_norm.to_numpy()).all()


def merge_upload(bucket, s3_key, new_df, dataset, region):
    """
    Merge newly fetched rows into the existing S3 CSV.GZ and re-upload it.

    Purpose:
        New rows are appended last, so drop_duplicates(keep="last") lets a
        freshly fetched row win for any natural key (handles watermark-day
        corrections). The full merged dataset is written back to the same
        S3 key, keeping the downstream TRUNCATE+COPY Redshift pipeline
        unchanged. When nothing changed the upload is skipped.

    Returns:
        tuple: (uploaded: bool, merged: pd.DataFrame). uploaded is True
        only when the S3 object was rewritten.
    """
    columns = list(new_df.columns)
    existing = _download_existing(bucket, s3_key, columns, region)

    if existing is None:
        merged = new_df.copy()
    else:
        combined = pd.concat([existing, new_df], ignore_index=True)
        merged = combined.drop_duplicates(
            subset=NATURAL_KEYS[dataset],
            keep="last"
        )
        merged = merged.sort_values(
            NATURAL_KEYS[dataset],
            na_position="last"
        ).reset_index(drop=True)

    if existing is not None and frames_equivalent(existing, merged):
        _LOGGER.info("No changes in dataset %s; skipping upload", dataset)
        return False, merged

    local_file = os.path.join(
        tempfile.gettempdir(),
        f"{dataset}.csv.gz"
    )

    merged.to_csv(
        local_file,
        index=False,
        compression="gzip"
    )

    s3 = boto3.client("s3", region_name=region)

    s3.upload_file(
        local_file,
        bucket,
        s3_key
    )

    _LOGGER.info("Created CSV gzip file: %s", local_file)
    _LOGGER.info("Uploaded successfully to s3://%s/%s", bucket, s3_key)

    return True, merged
