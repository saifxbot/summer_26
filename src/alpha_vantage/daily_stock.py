import configparser
import logging
import os
import tempfile
import time
from pathlib import Path

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

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config():
    config = configparser.ConfigParser()
    config_path = PROJECT_ROOT / "settings.ini"
    config.read(config_path)
    return config


def get_api_key():
    config = load_config()
    return config.get("credentials", "api_key")


def upload_to_s3(df):
    config = load_config()

    bucket = config.get("storage", "bucket_name")
    s3_key = config.get("storage", "daily_stock_key")
    region = config.get("aws", "region")

    local_file = os.path.join(
        tempfile.gettempdir(),
        "daily_stock.csv.gz"
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

    _LOGGER.info(
        "Created CSV gzip file: %s",
        local_file
    )

    _LOGGER.info(
        "Uploaded successfully to s3://%s/%s",
        bucket,
        s3_key
    )


def fetch_daily_stock(symbol):
    config = load_config()

    api_key = get_api_key()
    base_url = config.get("api", "base_url")
    function = config.get("daily_stock", "function")
    outputsize = config.get("daily_stock", "outputsize")

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&symbol={symbol}"
        f"&outputsize={outputsize}"
        f"&apikey={api_key}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    if "Time Series (Daily)" not in data:
        _LOGGER.error(
            "API did not return daily data for %s. Response: %s",
            symbol,
            data
        )
        return []

    time_series = data["Time Series (Daily)"]

    rows = []

    for stock_date, values in time_series.items():
        rows.append(
            {
                "stock_date": stock_date,
                "symbol": symbol,
                "open_price": values["1. open"],
                "high_price": values["2. high"],
                "low_price": values["3. low"],
                "close_price": values["4. close"],
                "volume": values["5. volume"],
            }
        )

    return rows


def get_daily_stocks():
    config = load_config()

    symbols = config.get(
        "daily_stock",
        "symbols"
    ).split(",")

    all_rows = []

    for symbol in symbols:
        symbol = symbol.strip()

        _LOGGER.info(
            "Fetching daily stock data for %s",
            symbol
        )

        rows = fetch_daily_stock(symbol)

        all_rows.extend(rows)

        time.sleep(1)

    df = pd.DataFrame(all_rows)

    _LOGGER.info(
        "Total daily stock rows fetched: %s",
        len(df)
    )

    if not df.empty:
        _LOGGER.info(
            "Daily stock sample:\n%s",
            df[
                [
                    "stock_date",
                    "symbol",
                    "open_price",
                    "close_price",
                    "volume"
                ]
            ].head(10).to_string(index=False)
        )

    upload_to_s3(df)


if __name__ == "__main__":
    get_daily_stocks()