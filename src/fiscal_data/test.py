import time
import requests

url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"

page_number = 1
page_size = 1000
all_rows = []


def get_with_retry(url, params, max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            if response.status_code == 400:
                print("400 received. Probably no more pages.")
                return None

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as error:
            print(f"Attempt {attempt} failed: {error}")

            if attempt == max_retries:
                raise

            time.sleep(attempt * 2)


while True:
    params = {
        "page[number]": page_number,
        "page[size]": page_size,
        "sort": "record_date",
        "format": "json"
    }

    response = get_with_retry(url, params)

    if response is None:
        break

    data = response.json()
    rows = data.get("data", [])

    print(f"Page {page_number}: {len(rows)} rows")

    if not rows:
        break

    all_rows.extend(rows)

    if len(rows) < page_size:
        break

    page_number += 1

print("Total rows:", len(all_rows))

if all_rows:
    print("Columns:", list(all_rows[0].keys()))
    print("Sample row:", all_rows[0])