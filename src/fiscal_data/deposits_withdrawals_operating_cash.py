import configparser
import logging
import os
import tempfile
import time

import boto3
import pandas as pd
import requests


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


def clean_value(value):
    if value is None:
        return None

    value = str(value).strip()

    if value in [
        "",
        "None",
        "none",
        "NULL",
        "null",
        "-",
        "N/A",
        "n/a",
        "NaN",
        "nan"
    ]:
        return None

    return value


def clean_numeric(value):
    value = clean_value(value)

    if value is None:
        return None

    return value.replace(",", "").strip()


def get_with_retry(url, params, max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code == 400:
                return None

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as error:
            _LOGGER.warning(
                "Attempt %s failed: %s",
                attempt,
                error
            )

            if attempt == max_retries:
                raise

            time.sleep(attempt * 2)


def map_deposits_withdrawals_operating_cash(row):
    return {
        "record_date": clean_value(row.get("record_date")),
        "account_type": clean_value(row.get("account_type")),
        "transaction_type": clean_value(row.get("transaction_type")),
        "transaction_catg": clean_value(row.get("transaction_catg")),
        "transaction_catg_desc": clean_value(row.get("transaction_catg_desc")),
        "transaction_today_amt": clean_numeric(row.get("transaction_today_amt")),
        "transaction_mtd_amt": clean_numeric(row.get("transaction_mtd_amt")),
        "transaction_fytd_amt": clean_numeric(row.get("transaction_fytd_amt")),
        "table_nbr": clean_value(row.get("table_nbr")),
        "table_nm": clean_value(row.get("table_nm")),
        "src_line_nbr": clean_numeric(row.get("src_line_nbr")),
        "record_fiscal_year": clean_numeric(row.get("record_fiscal_year")),
        "record_fiscal_quarter": clean_numeric(row.get("record_fiscal_quarter")),
        "record_calendar_year": clean_numeric(row.get("record_calendar_year")),
        "record_calendar_quarter": clean_numeric(row.get("record_calendar_quarter")),
        "record_calendar_month": clean_numeric(row.get("record_calendar_month")),
        "record_calendar_day": clean_numeric(row.get("record_calendar_day")),
    }


def fetch_deposits_withdrawals_operating_cash():
    config = load_config()

    base_url = config.get("fiscaldata", "base_url")
    endpoint = config.get(
        "deposits_withdrawals_operating_cash",
        "endpoint"
    )
    page_size = config.getint(
        "deposits_withdrawals_operating_cash",
        "page_size"
    )

    url = f"{base_url}{endpoint}"

    page_number = 1
    rows = []

    while True:
        params = {
            "page[number]": page_number,
            "page[size]": page_size,
            "sort": "record_date",
            "format": "json"
        }

        _LOGGER.info("Fetching page %s", page_number)

        response = get_with_retry(url, params)

        if response is None:
            _LOGGER.info("No more pages available")
            break

        data = response.json()
        page_rows = data.get("data", [])

        _LOGGER.info(
            "Page %s rows fetched: %s",
            page_number,
            len(page_rows)
        )

        if not page_rows:
            break

        for row in page_rows:
            rows.append(map_deposits_withdrawals_operating_cash(row))

        if len(page_rows) < page_size:
            break

        page_number += 1

    df = pd.DataFrame(rows)

    _LOGGER.info(
        "Total deposits withdrawals operating cash rows fetched: %s",
        len(df)
    )

    if not df.empty:
        _LOGGER.info(
            "Deposits withdrawals operating cash sample:\n%s",
            df.head(5).to_string(index=False)
        )

    return df


def upload_to_s3(df):
    config = load_config()

    bucket = config.get("storage", "bucket_name")
    s3_key = config.get(
        "storage",
        "deposits_withdrawals_operating_cash_key"
    )
    region = config.get("aws", "region")

    local_file = os.path.join(
        tempfile.gettempdir(),
        "deposits_withdrawals_operating_cash.csv.gz"
    )

    df.to_csv(
        local_file,
        index=False,
        compression="gzip"
    )

    s3 = boto3.client(
        "s3",
        region_name=region
    )

    s3.upload_file(
        local_file,
        bucket,
        s3_key
    )

    _LOGGER.info("Created CSV gzip file: %s", local_file)
    _LOGGER.info("Uploaded successfully to s3://%s/%s", bucket, s3_key)


def main():
    df = fetch_deposits_withdrawals_operating_cash()

    if df.empty:
        raise Exception("No deposits withdrawals operating cash data fetched")

    upload_to_s3(df)


if __name__ == "__main__":
    main()