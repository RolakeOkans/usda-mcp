import requests
import os
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("NASS_API_KEY")
BASE_URL = "https://quickstats.nass.usda.gov/api/api_GET/"

def get_nass_data(commodity: str, statistic: str, state: str, year: int) -> dict:
    """
    Retrieve USDA NASS agricultural data.

    commodity: the crop e.g. CORN, SOYBEANS
    statistic: what to measure e.g. AREA PLANTED, YIELD, PRODUCTION, PRICE RECEIVED
    state: two letter state code e.g. IA, IL, MN
    year: the year e.g. 2022

    Returns a dictionary with the value and unit.
    """

    # clean inputs
    commodity = commodity.upper().strip()
    statistic = statistic.upper().strip()
    state = state.upper().strip()

    # validate inputs
    if not KEY:
        return {"error": "NASS API key not configured"}
    if len(state) != 2:
        return {"error": f"Invalid state code: {state}. Use two letter code like IA or IL"}
    if year < 1900 or year > 2026:
        return {"error": f"Invalid year: {year}"}

    # build params
    params = {
        "key": KEY,
        "commodity_desc": commodity,
        "statisticcat_desc": statistic,
        "state_alpha": state,
        "year": year,
        "agg_level_desc": "STATE",
        "domain_desc": "TOTAL",
        "freq_desc": "ANNUAL",
        "source_desc": "SURVEY",
        "format": "JSON"
    }

    # price received uses a different reference period
    if statistic == "PRICE RECEIVED":
        params["reference_period_desc"] = "MARKETING YEAR"
    else:
        params["reference_period_desc"] = "YEAR"

    # corn yield needs grain filter
    if commodity == "CORN" and statistic == "YIELD":
        params["util_practice_desc"] = "GRAIN"

    # production should return bushels not dollars
    if statistic == "PRODUCTION":
        params["unit_desc"] = "BU"

    # make the API call
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("data"):
            return {"error": f"No data found for {commodity} {statistic} in {state} for {year}"}

        item = data["data"][0]
        return {
            "commodity": item["commodity_desc"],
            "statistic": item["statisticcat_desc"],
            "value": item["Value"],
            "unit": item["unit_desc"],
            "state": item["state_name"],
            "year": item["year"]
        }

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}