import configparser
import os
import tempfile
from datetime import datetime, UTC

import boto3
import pandas as pd
import requests


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

BUCKET_NAME = "summer-26-project"
S3_KEY = "exchange_rates/exchange_rates.csv.gz"
AWS_REGION = "eu-west-1"


def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, "settings.ini")
    config.read(config_path)
    return config


def get_api_key():
    config = load_config()
    return config.get("credentials", "api_key")


def upload_exchange_rates_to_s3(exchange_rate_data):
    df = pd.DataFrame(exchange_rate_data)

    local_file = os.path.join(
        tempfile.gettempdir(),
        "exchange_rates.csv.gz"
    )

    df.to_csv(local_file, index=False, compression="gzip")

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.upload_file(local_file, BUCKET_NAME, S3_KEY)

    print(f"Created CSV gzip file: {local_file}")
    print(f"Uploaded successfully to s3://{BUCKET_NAME}/{S3_KEY}")


def get_exchange_rate():
    config = load_config()

    api_key = get_api_key()

    base_url = config.get("api", "base_url")
    function = config.get("exchange_rate", "function")
    from_currency = config.get("exchange_rate", "from_currency")
    to_currency = config.get("exchange_rate", "to_currency")

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&from_currency={from_currency}"
        f"&to_currency={to_currency}"
        f"&apikey={api_key}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()
    exchange_data = data["Realtime Currency Exchange Rate"]

    exchange_rate_data = [
        {
            "rate_date": datetime.now(UTC).date().isoformat(),
            "from_currency": exchange_data["1. From_Currency Code"],
            "to_currency": exchange_data["3. To_Currency Code"],
            "exchange_rate": exchange_data["5. Exchange Rate"],
        }
    ]

    print("\nExchange Rate Data:\n")

    for item in exchange_rate_data:
        print(
            f"{item['rate_date']} "
            f"{item['from_currency']} to {item['to_currency']} "
            f"Rate: {item['exchange_rate']}"
        )

    upload_exchange_rates_to_s3(exchange_rate_data)


if __name__ == "__main__":
    get_exchange_rate()