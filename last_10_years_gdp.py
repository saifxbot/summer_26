import requests
import json
import boto3
from botocore.exceptions import ClientError
import configparser
import os
from extract_endpoint import extract_endpoint, format_gdp_data

def load_config():
    """Load configuration from settings.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'settings.ini')
    config.read(config_path)
    return config

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
    config = load_config()
    
    function = config.get('api', 'function')
    interval = config.get('api', 'interval')
    years_to_fetch = config.getint('data', 'years_to_fetch')
    
    # Use the generic endpoint extractor
    data = extract_endpoint(function, interval=interval)
    
    if data:
        format_gdp_data(data, limit=years_to_fetch)


# Method call
get_last_10_years_gdp()