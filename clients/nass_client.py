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
    

def query_nass_flexible(
    commodity: str,
    statistic: str,
    state: str = None,
    year: int = None,
    year_gte: int = None,
    year_lte: int = None,
    agg_level: str = "STATE",
    unit: str = None,
    util_practice: str = None,
    source: str = "SURVEY"
) -> dict:
    """
    Flexible NASS query that handles any valid question about USDA agricultural data.

    commodity: the crop e.g. CORN, SOYBEANS, WHEAT, COTTON
    statistic: what to measure e.g. AREA PLANTED, AREA HARVESTED, YIELD, 
               PRODUCTION, PRICE RECEIVED, INVENTORY
    state: two letter state code e.g. IA, IL, MN. Leave empty for national data.
    year: specific year e.g. 2022
    year_gte: get data from this year onwards e.g. 2018 (for trends)
    year_lte: get data up to this year e.g. 2022 (for trends)
    agg_level: geographic level - STATE, NATIONAL, or COUNTY
    unit: unit of measurement e.g. ACRES, BU, BU / ACRE. Leave empty to get all units.
    util_practice: e.g. GRAIN for corn yield
    source: SURVEY or CENSUS
    """

    if not KEY:
        return {"error": "NASS API key not configured"}

    commodity = commodity.upper().strip()
    statistic = statistic.upper().strip()

    params = {
        "key": KEY,
        "commodity_desc": commodity,
        "statisticcat_desc": statistic,
        "agg_level_desc": agg_level.upper(),
        "domain_desc": "TOTAL",
        "freq_desc": "ANNUAL",
        "source_desc": source,
        "format": "JSON"
    }

    # location
    if state:
        params["state_alpha"] = state.upper().strip()

    # time
    if year:
        params["year"] = year
    if year_gte:
        params["year__GE"] = year_gte
    if year_lte:
        params["year__LE"] = year_lte

    # unit filter
    if unit:
        params["unit_desc"] = unit

    # util practice
    if util_practice:
        params["util_practice_desc"] = util_practice

    # smart defaults based on statistic
    if statistic == "PRICE RECEIVED":
        params["reference_period_desc"] = "MARKETING YEAR"
    else:
        params["reference_period_desc"] = "YEAR"

    if commodity == "CORN" and statistic == "YIELD" and not util_practice:
        params["util_practice_desc"] = "GRAIN"

    if statistic == "PRODUCTION" and not unit:
        params["unit_desc"] = "BU"

    # check count first to avoid hitting 50k limit
    try:
        count_url = "https://quickstats.nass.usda.gov/api/get_counts/"
        count_response = requests.get(count_url, params=params, timeout=10)
        count_data = count_response.json()
        count = int(count_data.get("count", 0))

        if count == 0:
            return {"error": f"No data found for {commodity} {statistic}. Try different parameters."}
        if count > 50000:
            return {"error": f"Query too broad — would return {count} records. Please narrow down by adding state or year."}

    except Exception:
        pass

    # make the actual data call
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("data"):
            return {"error": f"No data found for {commodity} {statistic}"}

        results = []
        for item in data["data"]:
            if item.get("Value") not in ["(D)", "(Z)", "", " "]:
                results.append({
                    "commodity": item["commodity_desc"],
                    "statistic": item["statisticcat_desc"],
                    "value": item["Value"],
                    "unit": item["unit_desc"],
                    "location": item.get("state_name") or item.get("location_desc"),
                    "year": item["year"],
                    "period": item.get("reference_period_desc")
                })

        if len(results) == 1:
            return results[0]
        return {"count": len(results), "data": results}

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}