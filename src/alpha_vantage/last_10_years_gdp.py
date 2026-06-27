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


def upload_gdp_to_s3(gdp_data):
    config = load_config()

    bucket = config.get("storage", "bucket_name")
    s3_key = config.get("storage", "gdp_key")
    region = config.get("aws", "region")

    df = pd.DataFrame(gdp_data)

    local_file = os.path.join(
        tempfile.gettempdir(),
        "real_gdp.csv.gz"
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


def get_last_10_years_gdp():
    config = load_config()
    api_key = get_api_key()

    base_url = config.get("api", "base_url")
    function = config.get("api", "function")
    interval = config.get("api", "interval")
    years_to_fetch = config.getint("data", "years_to_fetch")

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&interval={interval}"
        f"&apikey={api_key}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    if "data" not in data:
        _LOGGER.error(
            "API response: %s",
            data
        )
        raise Exception("API did not return GDP data.")

    gdp_data = data["data"][:years_to_fetch]

    _LOGGER.info(
        "Last %s Years Real GDP",
        years_to_fetch
    )

    for item in gdp_data:
        _LOGGER.info(
            "Year: %s GDP: %s",
            item["date"],
            item["value"]
        )

    upload_gdp_to_s3(gdp_data)


if __name__ == "__main__":
    get_last_10_years_gdp()