import requests
import os
from dotenv import load_dotenv

load_dotenv()

AMS_KEY = os.getenv("AMS_API_KEY")

# try exactly as shown in the docs
url = "https://marsapi.ams.usda.gov/services/v1.2/reports/3046/Report Detail"
params = {"q": "commodity=Corn,Soybeans"}

response = requests.get(url, auth=(AMS_KEY, ""), params=params)
print(response.status_code)
data = response.json()
print(type(data))
print(data)

from clients.ams_client import get_ams_price

print(get_ams_price("Corn", "minneapolis"))
print(get_ams_price("Soybeans", "minneapolis"))
print(get_ams_price("Corn", "iowa"))

from clients.ams_client import get_ams_price, get_ams_price_comparison

# test different locations
print(get_ams_price("Corn", "texas"))
print(get_ams_price("Wheat", "kansas"))
print(get_ams_price("Corn", "north dakota"))

# test comparison
print("\n--- COMPARISON ---")
results = get_ams_price_comparison("Corn", ["iowa", "illinois", "nebraska", "kansas"])
for r in results:
    print(f"{r['region']}: ${r['avg_price']} / bu")