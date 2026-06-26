import configparser
import json
import os
import tempfile
import time

import boto3
import pandas as pd
import requests


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def load_config():
    config = configparser.ConfigParser()

    config.read(
        os.path.join(
            PROJECT_ROOT,
            "settings.ini"
        )
    )

    return config


def get_api_key():
    config = load_config()

    return config.get(
        "credentials",
        "api_key"
    )


def clean_value(value):

    if value in [
        None,
        "",
        "None",
        "-",
        "N/A"
    ]:
        return None

    return value


def upload_to_s3(df):

    config = load_config()

    bucket = config.get(
        "storage",
        "bucket_name"
    )

    s3_key = config.get(
        "storage",
        "news_sentiment_key"
    )

    region = config.get(
        "aws",
        "region"
    )

    local_file = os.path.join(
        tempfile.gettempdir(),
        "news_sentiment.csv.gz"
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

    print(
        f"Uploaded successfully to s3://{bucket}/{s3_key}"
    )


def fetch_news(symbol):

    config = load_config()

    limit = config.getint(
        "news_sentiment",
        "limit"
    )

    base_url = config.get(
        "api",
        "base_url"
    )

    function = config.get(
        "news_sentiment",
        "function"
    )

    api_key = get_api_key()

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&tickers={symbol}"
        f"&apikey={api_key}"
    )

    response = requests.get(
        url
    )

    response.raise_for_status()

    data = response.json()

    if "feed" not in data:

        print(
            f"No news for {symbol}"
        )

        return []

    feed = data["feed"][:limit]

    rows = []

    for item in feed:

        rows.append(
            {
                "time_published":
                clean_value(
                    item.get(
                        "time_published"
                    )
                ),

                "title":
                clean_value(
                    item.get(
                        "title"
                    )
                ),

                "url":
                clean_value(
                    item.get(
                        "url"
                    )
                ),

                "authors":
                json.dumps(
                    item.get(
                        "authors"
                    )
                ),

                "summary":
                clean_value(
                    item.get(
                        "summary"
                    )
                ),

                "banner_image":
                clean_value(
                    item.get(
                        "banner_image"
                    )
                ),

                "source":
                clean_value(
                    item.get(
                        "source"
                    )
                ),

                "category_within_source":
                clean_value(
                    item.get(
                        "category_within_source"
                    )
                ),

                "source_domain":
                clean_value(
                    item.get(
                        "source_domain"
                    )
                ),

                "topics":
                json.dumps(
                    item.get(
                        "topics"
                    )
                ),

                "overall_sentiment_score":
                clean_value(
                    item.get(
                        "overall_sentiment_score"
                    )
                ),

                "overall_sentiment_label":
                clean_value(
                    item.get(
                        "overall_sentiment_label"
                    )
                ),

                "ticker_sentiment":
                json.dumps(
                    item.get(
                        "ticker_sentiment"
                    )
                )
            }
        )

    return rows


def get_news_sentiment():

    config = load_config()

    symbols = config.get(
        "news_sentiment",
        "symbols"
    ).split(",")

    all_rows = []

    for symbol in symbols:

        symbol = symbol.strip()

        rows = fetch_news(
            symbol
        )

        print(
            f"{symbol}: {len(rows)} rows"
        )

        all_rows.extend(
            rows
        )

        time.sleep(1)

    df = pd.DataFrame(
        all_rows
    )

    print(
        f"Total rows: {len(df)}"
    )

    if df.empty:

        print(
            "No rows found"
        )

        return

    df = df.drop_duplicates(
        subset=[
            "time_published",
            "url"
        ]
    )

    upload_to_s3(
        df
    )


if __name__ == "__main__":
    get_news_sentiment()