from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch"
PARAMS = {
    "market": 0,
    "paperTypes[0]": 1,
    "paperTypes[1]": 2,
    "paperTypes[2]": 3,
    "paperTypes[3]": 4,
    "paperTypes[4]": 5,
    "paperTypes[5]": 6,
    "paperTypes[6]": 7,
    "paperTypes[7]": 8,
    "paperTypes[8]": 9,
    "withBestLimits": "false",
    "hEven": 0,
    "RefID": 0,
}

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "snapshots"
OUT.mkdir(parents=True, exist_ok=True)

session = requests.Session()
retry = Retry(total=4, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
session.mount("https://", HTTPAdapter(max_retries=retry))
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

r = session.get(URL, params=PARAMS, headers=headers, timeout=60)
r.raise_for_status()
payload = r.json()
rows = payload.get("marketwatch", [])
if not isinstance(rows, list) or not rows:
    raise RuntimeError(f"Unexpected TSETMC response: {type(rows).__name__}")

df = pd.DataFrame(rows)
for c in ["insCode", "lVal18AFC", "lVal30", "dEven", "hEven", "pClosing", "pDrCotVal", "qTotTran5J", "qTotCap", "zTotTran", "priceMin", "priceMax", "priceYesterday", "priceFirst"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="ignore")

df["collected_at_utc"] = datetime.now(timezone.utc).isoformat()
df["source"] = "tsetmc_cdn_marketwatch"

day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
csv_path = OUT / f"market_watch_{day}.csv"
json_path = OUT / f"market_watch_{day}.json"
df.to_csv(csv_path, index=False, encoding="utf-8-sig")
json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

print(f"OK rows={len(df)}")
print(f"CSV={csv_path}")
print(f"JSON={json_path}")
