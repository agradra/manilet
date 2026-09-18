from pprint import pprint

import requests

url_binance_s = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT"
resp = requests.get(url_binance_s, timeout=5)
pprint(resp.json())

