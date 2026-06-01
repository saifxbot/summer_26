import requests

API_KEY = "N4L5M3W3LLXA9XYB"

def get_last_10_years_gdp():
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=REAL_GDP"
        f"&interval=annual"
        f"&apikey={API_KEY}"
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