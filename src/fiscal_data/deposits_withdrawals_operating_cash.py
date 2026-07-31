import argparse
import configparser
import logging
import os
import re
import time

import pandas as pd
import requests

from dynamodb_state import get_watermark, merge_upload, set_watermark


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


def get_with_retry(url, params, max_retries=10):
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

            time.sleep(min(attempt * 5, 60))


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
        "sub_table_name": clean_value(row.get("sub_table_name")),
        "src_line_nbr": clean_numeric(row.get("src_line_nbr")),
        "record_fiscal_year": clean_numeric(row.get("record_fiscal_year")),
        "record_fiscal_quarter": clean_numeric(row.get("record_fiscal_quarter")),
        "record_calendar_year": clean_numeric(row.get("record_calendar_year")),
        "record_calendar_quarter": clean_numeric(row.get("record_calendar_quarter")),
        "record_calendar_month": clean_numeric(row.get("record_calendar_month")),
        "record_calendar_day": clean_numeric(row.get("record_calendar_day")),
    }


def fetch_deposits_withdrawals_operating_cash(watermark=None, full=False):
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

    if watermark is not None and not full:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", watermark):
            raise ValueError(
                f"Invalid watermark format for deposits_withdrawals_operating_cash: {watermark!r}"
            )

        date_filter = f"record_date:gte:{watermark}"
    else:
        date_filter = None

    page_number = 1
    rows = []

    while True:
        params = {
            "page[number]": page_number,
            "page[size]": page_size,
            "sort": "record_date",
            "format": "json"
        }

        if date_filter is not None:
            params["filter"] = date_filter

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


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Treasury deposits and withdrawals of operating cash data"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force a full reload of all history (ignores watermark)"
    )
    args = parser.parse_args()

    config = load_config()
    dataset = "deposits_withdrawals_operating_cash"

    bucket = config.get("storage", "bucket_name")
    s3_key = config.get(
        "storage",
        "deposits_withdrawals_operating_cash_key"
    )
    region = config.get("aws", "region")

    watermark = None if args.full else get_watermark(dataset)

    df = fetch_deposits_withdrawals_operating_cash(
        watermark=watermark,
        full=args.full
    )

    if df.empty:
        if args.full:
            raise Exception("No deposits withdrawals operating cash data fetched")

        _LOGGER.info("No new deposits withdrawals operating cash data; nothing to do")
        return

    uploaded, merged = merge_upload(
        bucket,
        s3_key,
        df,
        dataset,
        region
    )

    if uploaded:
        set_watermark(dataset, str(merged["record_date"].max()), len(merged))


if __name__ == "__main__":
    main()