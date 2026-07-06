import configparser
import logging
import os
import tempfile
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
    s3_key = config.get("storage", "exchange_rate_key")
    region = config.get("aws", "region")

    local_file = os.path.join(
        tempfile.gettempdir(),
        "exchange_rates.csv.gz"
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


def get_exchange_rates():
    config = load_config()

    api_key = get_api_key()

    base_url = config.get("api", "base_url")
    function = config.get("exchange_rate", "function")
    from_currency = config.get("exchange_rate", "from_currency")
    to_currency = config.get("exchange_rate", "to_currency")
    outputsize = config.get("exchange_rate", "outputsize")

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&from_symbol={from_currency}"
        f"&to_symbol={to_currency}"
        f"&outputsize={outputsize}"
        f"&apikey={api_key}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    if "Time Series FX (Daily)" not in data:
        _LOGGER.error("API response: %s", data)
        raise Exception("API did not return exchange rate data.")

    time_series = data["Time Series FX (Daily)"]

    rows = []

    for rate_date, values in time_series.items():
        rows.append(
            {
                "rate_date": rate_date,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": values["4. close"],
            }
        )

    df = pd.DataFrame(rows)

    _LOGGER.info(
        "Total exchange rate rows fetched: %s",
        len(df)
    )

    upload_to_s3(df)


if __name__ == "__main__":
    get_exchange_rates()