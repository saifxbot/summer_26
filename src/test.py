import configparser
import requests

config = configparser.ConfigParser()
config.read("../settings.ini")

api_key = config.get("credentials", "api_key")

url = (
    "https://www.alphavantage.co/query"
    "?function=NEWS_SENTIMENT"
    "&tickers=IBM"
    "&limit=5"
    f"&apikey={api_key}"
)

response = requests.get(url)

data = response.json()

print(data.keys())

if "feed" in data:
    print(data["feed"][0])
else:
    print(data)