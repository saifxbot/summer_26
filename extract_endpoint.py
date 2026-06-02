import requests
import json
import boto3
from botocore.exceptions import ClientError
import configparser
import os

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

def extract_endpoint(endpoint_name, **kwargs):
    """
    Generic method to extract data from any AlphaVantage endpoint
    
    Args:
        endpoint_name (str): The AlphaVantage function name (e.g., 'REAL_GDP', 'INFLATION', etc.)
        **kwargs: Optional parameters like interval, data_type, etc.
    
    Returns:
        dict: API response data
    """
    config = load_config()
    api_key = get_api_key()
    
    base_url = config.get('api', 'base_url')
    
    # Build URL with endpoint name and parameters
    url = f"{base_url}?function={endpoint_name}&apikey={api_key}"
    
    # Add optional parameters
    for key, value in kwargs.items():
        url += f"&{key}={value}"
    
    print(f"[*] Fetching data from endpoint: {endpoint_name}")
    print(f"[*] URL: {url.replace(api_key, '***')}")
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for API errors
            if "Error Message" in data:
                print(f"[!] API Error: {data['Error Message']}")
                return None
            
            if "Note" in data:
                print(f"[!] API Rate Limit: {data['Note']}")
                return None
            
            print(f"[+] Successfully retrieved data from {endpoint_name}")
            return data
        else:
            print(f"[!] Request failed with status code: {response.status_code}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"[!] Request error: {e}")
        return None

def format_gdp_data(data, limit=10):
    """
    Format and display GDP data from API response
    
    Args:
        data (dict): API response data
        limit (int): Number of records to display
    """
    if not data or "data" not in data:
        print("[!] No data available to display")
        return
    
    gdp_data = data["data"][:limit]
    
    print(f"\nLast {limit} Years Real GDP:\n")
    for item in gdp_data:
        print(f"Year: {item['date']} GDP: {item['value']}")

def format_generic_data(data, key_field="date", value_field="value", limit=10):
    """
    Generic formatter for any endpoint data
    
    Args:
        data (dict): API response data
        key_field (str): Field name to use as key (default: 'date')
        value_field (str): Field name to use as value (default: 'value')
        limit (int): Number of records to display
    """
    if not data or "data" not in data:
        print("[!] No data available to display")
        return
    
    endpoint_data = data["data"][:limit]
    
    print(f"\nData Results (showing {min(len(endpoint_data), limit)} records):\n")
    for item in endpoint_data:
        key = item.get(key_field, "N/A")
        value = item.get(value_field, "N/A")
        print(f"{key_field}: {key} | {value_field}: {value}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_endpoint.py <ENDPOINT_NAME> [--limit LIMIT]")
        print("\nExamples:")
        print("  python extract_endpoint.py REAL_GDP")
        print("  python extract_endpoint.py INFLATION --limit 5")
        print("  python extract_endpoint.py UNEMPLOYMENT --limit 10")
        sys.exit(1)
    
    endpoint = sys.argv[1]
    limit = 10
    params = {}
    
    # Parse command line arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--limit':
            limit = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--interval':
            params['interval'] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Extract endpoint data
    data = extract_endpoint(endpoint, **params)
    
    if data:
        # Format based on endpoint type
        if endpoint == "REAL_GDP":
            format_gdp_data(data, limit)
        else:
            format_generic_data(data, limit=limit)
