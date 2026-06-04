import configparser
import os

import boto3
import requests
from botocore.exceptions import ClientError


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def load_config():
    """Load configuration from settings.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, 'settings.ini')
    config.read(config_path)
    return config


def get_api_key():
    """Fetch API key from AWS Secrets Manager"""
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if api_key:
        return api_key

    secret_name = "gdp-api-key"
    region = "eu-west-1"

    try:
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise


def get_last_10_years_gdp():
    config = load_config()
    api_key = get_api_key()

    base_url = config.get('api', 'base_url')
    function = config.get('api', 'function')
    interval = config.get('api', 'interval')
    years_to_fetch = config.getint('data', 'years_to_fetch')

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&interval={interval}"
        f"&apikey={api_key}"
    )
    # Make the API call
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        gdp_data = data["data"][:years_to_fetch]

        print("\nLast 10 Years Real GDP:\n")

        for item in gdp_data:
            print(f"Year: {item['date']} GDP: {item['value']}")

    else:
        print("Request failed:", response.status_code)


# Method call
get_last_10_years_gdp()
