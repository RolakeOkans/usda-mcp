from clients.nass_client import get_nass_data

# test all 8 queries
print(get_nass_data("CORN", "AREA PLANTED", "IA", 2022))
print(get_nass_data("CORN", "YIELD", "IA", 2022))
print(get_nass_data("CORN", "PRODUCTION", "IA", 2022))
print(get_nass_data("CORN", "PRICE RECEIVED", "IA", 2022))
print(get_nass_data("SOYBEANS", "AREA PLANTED", "IA", 2022))
print(get_nass_data("SOYBEANS", "YIELD", "IA", 2022))
print(get_nass_data("SOYBEANS", "PRODUCTION", "IA", 2022))
print(get_nass_data("SOYBEANS", "PRICE RECEIVED", "IA", 2022))