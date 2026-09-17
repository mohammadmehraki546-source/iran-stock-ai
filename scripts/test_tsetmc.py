import json
import requests

URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch?market=0&paperTypes[0]=1&paperTypes[1]=2&paperTypes[2]=3&paperTypes[3]=4&paperTypes[4]=5&paperTypes[5]=6&paperTypes[6]=7&paperTypes[7]=8&paperTypes[8]=9&withBestLimits=false&hEven=0&RefID=0"

r = requests.get(
    URL,
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
)
print("STATUS", r.status_code)
print("BYTES", len(r.content))
r.raise_for_status()
data = r.json()
print("TOP_KEYS", list(data)[:20] if isinstance(data, dict) else type(data).__name__)
print(json.dumps(data, ensure_ascii=False)[:5000])
