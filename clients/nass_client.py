import requests
import os
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("NASS_API_KEY")

BASE_URL = "https://quickstats.nass.usda.gov/api/api_GET/"

def query_nass(commodity, statistic, unit="", state="IA", year=2022, util_practice=None, reference_period="YEAR"):
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
        "source_desc": "SURVEY",
        "format": "JSON"
    }
    if unit:
        params["unit_desc"] = unit
    if util_practice:
        params["util_practice_desc"] = util_practice

    r = requests.get(BASE_URL, params=params)
    return r.json()
