import configparser
import os
import tempfile

import boto3
import pandas as pd
import requests
from botocore.exceptions import ClientError


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

BUCKET_NAME = "summer-26-project"
S3_KEY = "real_gdp/real_gdp.csv.gz"
AWS_REGION = "eu-west-1"


def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, "settings.ini")
    config.read(config_path)
    return config


def get_api_key():
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if api_key:
        return api_key

    secret_name = "gdp-api-key"

    try:
        client = boto3.client("secretsmanager", region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=secret_name)
        return response["SecretString"]
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise


def upload_gdp_to_s3(gdp_data):
    df = pd.DataFrame(gdp_data)

    local_file = os.path.join(tempfile.gettempdir(), "real_gdp.csv.gz")

    df.to_csv(local_file, index=False, compression="gzip")

    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.upload_file(local_file, BUCKET_NAME, S3_KEY)

    print(f"Created CSV gzip file: {local_file}")
    print(f"Uploaded successfully to s3://{BUCKET_NAME}/{S3_KEY}")


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

    gdp_data = data["data"][:years_to_fetch]

    print("\nLast 10 Years Real GDP:\n")

    for item in gdp_data:
        print(f"Year: {item['date']} GDP: {item['value']}")

    upload_gdp_to_s3(gdp_data)


if __name__ == "__main__":
    get_last_10_years_gdp()