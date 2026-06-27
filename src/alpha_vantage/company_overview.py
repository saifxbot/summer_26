import configparser
import logging
import os
import tempfile
import time
from pathlib import Path

import boto3
import pandas as pd
import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

_LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config():
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, "settings.ini")
    config.read(config_path)
    return config


def get_api_key():
    config = load_config()
    return config.get("credentials", "api_key")


def clean_value(value):
    if value in [None, "", "None", "-", "N/A"]:
        return None

    return value


def map_company_overview(data):
    return {
        "symbol": clean_value(data.get("Symbol")),
        "asset_type": clean_value(data.get("AssetType")),
        "name": clean_value(data.get("Name")),
        "description": clean_value(data.get("Description")),
        "cik": clean_value(data.get("CIK")),
        "exchange": clean_value(data.get("Exchange")),
        "currency": clean_value(data.get("Currency")),
        "country": clean_value(data.get("Country")),
        "sector": clean_value(data.get("Sector")),
        "industry": clean_value(data.get("Industry")),
        "address": clean_value(data.get("Address")),
        "official_site": clean_value(data.get("OfficialSite")),
        "fiscal_year_end": clean_value(data.get("FiscalYearEnd")),
        "latest_quarter": clean_value(data.get("LatestQuarter")),
        "market_capitalization": clean_value(data.get("MarketCapitalization")),
        "ebitda": clean_value(data.get("EBITDA")),
        "pe_ratio": clean_value(data.get("PERatio")),
        "peg_ratio": clean_value(data.get("PEGRatio")),
        "book_value": clean_value(data.get("BookValue")),
        "dividend_per_share": clean_value(data.get("DividendPerShare")),
        "dividend_yield": clean_value(data.get("DividendYield")),
        "eps": clean_value(data.get("EPS")),
        "revenue_per_share_ttm": clean_value(data.get("RevenuePerShareTTM")),
        "profit_margin": clean_value(data.get("ProfitMargin")),
        "operating_margin_ttm": clean_value(data.get("OperatingMarginTTM")),
        "return_on_assets_ttm": clean_value(data.get("ReturnOnAssetsTTM")),
        "return_on_equity_ttm": clean_value(data.get("ReturnOnEquityTTM")),
        "revenue_ttm": clean_value(data.get("RevenueTTM")),
        "gross_profit_ttm": clean_value(data.get("GrossProfitTTM")),
        "analyst_target_price": clean_value(data.get("AnalystTargetPrice")),
        "beta": clean_value(data.get("Beta")),
        "week_52_high": clean_value(data.get("52WeekHigh")),
        "week_52_low": clean_value(data.get("52WeekLow")),
        "shares_outstanding": clean_value(data.get("SharesOutstanding")),
        "dividend_date": clean_value(data.get("DividendDate")),
        "ex_dividend_date": clean_value(data.get("ExDividendDate")),
    }


def upload_to_s3(df):
    config = load_config()

    bucket = config.get("storage", "bucket_name")
    s3_key = config.get("storage", "company_overview_key")
    region = config.get("aws", "region")

    local_file = os.path.join(
        tempfile.gettempdir(),
        "company_overview.csv.gz"
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

    _LOGGER.info("Created CSV gzip file: %s", local_file)
    _LOGGER.info("Uploaded successfully to s3://%s/%s", bucket, s3_key)


def fetch_company_overview(symbol):
    config = load_config()

    api_key = get_api_key()
    base_url = config.get("api", "base_url")
    function = config.get("company_overview", "function")

    url = (
        f"{base_url}"
        f"?function={function}"
        f"&symbol={symbol}"
        f"&apikey={api_key}"
    )

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    return map_company_overview(data)


def get_company_overviews():
    config = load_config()

    symbols = config.get(
        "company_overview",
        "symbols"
    ).split(",")

    rows = []

    for symbol in symbols:
        symbol = symbol.strip()

        _LOGGER.info("Fetching company overview for %s", symbol)

        row = fetch_company_overview(symbol)

        if row["symbol"]:
            rows.append(row)
        else:
            _LOGGER.warning("No data returned for %s", symbol)

        time.sleep(1)

    df = pd.DataFrame(rows)

    _LOGGER.info("Total company overview rows fetched: %s", len(df))

    if not df.empty:
        _LOGGER.info(
            "Company overview sample:\n%s",
            df[["symbol", "name", "sector", "industry"]].to_string(index=False)
        )

    upload_to_s3(df)


if __name__ == "__main__":
    get_company_overviews()