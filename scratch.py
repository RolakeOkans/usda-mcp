import requests
import os
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("NASS_API_KEY")

def query_nass(commodity, statistic, unit, state="IA", year=2022, util_practice=None, source="SURVEY", reference_period="YEAR"):
    params = {
        "key": KEY,
        "commodity_desc": commodity,
        "statisticcat_desc": statistic,
        "state_alpha": state,
        "year": year,
        "agg_level_desc": "STATE",
        "domain_desc": "TOTAL",
        "reference_period_desc": reference_period,
        "freq_desc": "ANNUAL",
        "source_desc": source,
        "format": "JSON"
    }
    if unit:
        params["unit_desc"] = unit
    if util_practice:
        params["util_practice_desc"] = util_practice

    r = requests.get("https://quickstats.nass.usda.gov/api/api_GET/", params=params)
    data = r.json()
    if not data.get("data"):
        print(f"{commodity} | {statistic} | NO DATA RETURNED")
    else:
        for item in data["data"]:
            print(f"{item['commodity_desc']} | {item['statisticcat_desc']} | {item['Value']} {item['unit_desc']}")
    print("---")

query_nass("CORN",     "AREA PLANTED",   "ACRES")
query_nass("CORN",     "YIELD",          "BU / ACRE", util_practice="GRAIN")
query_nass("CORN",     "PRODUCTION",     "BU")
query_nass("CORN",     "PRICE RECEIVED", "", reference_period="MARKETING YEAR")
query_nass("SOYBEANS", "AREA PLANTED",   "ACRES")
query_nass("SOYBEANS", "YIELD",          "BU / ACRE")
query_nass("SOYBEANS", "PRODUCTION",     "BU")
query_nass("SOYBEANS", "PRICE RECEIVED", "", reference_period="MARKETING YEAR")