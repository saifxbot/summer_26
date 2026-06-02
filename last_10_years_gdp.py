import requests
import json
import boto3
from botocore.exceptions import ClientError

def get_api_key():
    """Fetch API key from AWS Secrets Manager"""
    secret_name = "gdp-api-key"
    region = "eu-north-1"
    
    try:
        client = boto3.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise

def get_last_10_years_gdp():
    api_key = get_api_key()
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=REAL_GDP"
        f"&interval=annual"
        f"&apikey={api_key}"
    )
# Make the API call
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        gdp_data = data["data"][:10]   # First 10 years returned

        print("\nLast 10 Years Real GDP:\n")

        for item in gdp_data:
            print(f"Year: {item['date']} GDP: {item['value']}")

    else:
        print("Request failed:", response.status_code)


# Method call
get_last_10_years_gdp()