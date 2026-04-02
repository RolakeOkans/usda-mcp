import requests
import os
from dotenv import load_dotenv

load_dotenv()

AMS_KEY = os.getenv("AMS_API_KEY")
BASE_URL = "https://marsapi.ams.usda.gov/services/v1.2/reports"

# cache report IDs so we don't search every time
_report_cache = {}

def find_grain_report(location: str) -> int | None:
    """
    Dynamically find the right AMS grain report ID for any location.
    Searches by location name and returns the most relevant daily grain report.
    """
    if location.lower() in _report_cache:
        return _report_cache[location.lower()]

    try:
        search_term = location.strip().split()[0]
        response = requests.get(
            BASE_URL,
            auth=(AMS_KEY, ""),
            params={"q": search_term},
            timeout=10
        )
        reports = response.json()

        if not isinstance(reports, list):
            return None

        for report in reports:
            title = report.get("report_title", "").lower()
            if "grain" in title and "daily" in title:
                slug_id = report.get("slug_id")
                _report_cache[location.lower()] = slug_id
                return slug_id

        return None

    except Exception:
        return None


def get_ams_price(
    commodity: str,
    location: str = "iowa",
    current_only: bool = True,
    transport_mode: str = None
) -> dict:
    """
    Get current grain market prices from USDA AMS Market News.

    commodity: any grain commodity e.g. Corn, Soybeans, Wheat, Oats, Sorghum, Canola
    location: any US state or city with a grain market e.g. iowa, kansas, minneapolis,
              texas, north dakota, nebraska, illinois, ohio, indiana, missouri
    current_only: True returns only today's cash price, False returns all contracts
    transport_mode: optional filter e.g. Truck, Rail, Barge

    Returns current price per bushel and market details.
    """

    if not AMS_KEY:
        return {"error": "AMS API key not configured"}

    commodity = commodity.strip().title()
    location = location.strip().lower()

    # known report IDs for common locations (fallback if search fails)
    known_reports = {
        "minneapolis": 3046,
        "iowa":        2850,
        "kansas":      2886,
        "illinois":    3192,
        "nebraska":    3225,
        "ohio":        2851,
        "texas":       2711,
        "missouri":    2932,
        "indiana":     3463,
        "south dakota": 3186,
        "north dakota": 3878,
        "minnesota":   3049,
        "arkansas":    2960,
        "tennessee":   3088,
        "kentucky":    2892,
        "virginia":    3167,
        "pennsylvania": 3091,
        "colorado":    2912,
        "california":  3146,
    }

    # get report ID
    report_id = known_reports.get(location)
    if not report_id:
        report_id = find_grain_report(location)
    if not report_id:
        available = ", ".join(known_reports.keys())
        return {"error": f"Could not find a grain price report for '{location}'. Try one of: {available}"}

    url = f"{BASE_URL}/{report_id}/Report Detail"
    params = {"q": f"commodity={commodity}"}

    try:
        response = requests.get(url, auth=(AMS_KEY, ""), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data if isinstance(data, list) else data.get("results", [])

        if not results:
            return {"error": f"No price data found for {commodity} in {location}"}

        # apply filters
        if current_only:
            current = [r for r in results if r.get("current") == "Yes"]
            if current:
                results = current

        if transport_mode:
            filtered = [r for r in results if
                       r.get("trans_mode", "").lower() == transport_mode.lower()]
            if filtered:
                results = filtered

        if not results:
            return {"error": f"No price found for {commodity} in {location}"}

        latest = results[0]
        result = {
            "commodity": latest.get("commodity"),
            "avg_price": latest.get("avg_price"),
            "price_min": latest.get("price Min"),
            "price_max": latest.get("price Max"),
            "price_unit": latest.get("price_unit"),
            "report_date": latest.get("report_date"),
            "location": latest.get("market_location_name"),
            "delivery_point": latest.get("delivery_point"),
            "transport_mode": latest.get("trans_mode"),
            "region": location
        }

        # include forward contract info if not current only
        if not current_only and latest.get("delivery_start"):
            result["delivery_start"] = latest.get("delivery_start")
            result["futures_month"] = latest.get("basis Min Futures Month")

        return result

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"AMS API request failed: {str(e)}"}


def get_ams_price_comparison(commodity: str, locations: list) -> list:
    """
    Compare grain prices across multiple locations.
    Useful for farmers deciding where to sell.

    commodity: e.g. Corn, Soybeans
    locations: list of locations e.g. ["iowa", "illinois", "nebraska"]

    Returns a sorted list of prices from highest to lowest.
    """
    results = []
    for location in locations:
        result = get_ams_price(commodity, location)
        if "error" not in result:
            results.append(result)

    # sort by avg_price highest first
    results.sort(key=lambda x: x.get("avg_price", 0), reverse=True)
    return results