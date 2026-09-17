from __future__ import annotations

import concurrent.futures
import json
import time
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MARKET_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetMarketWatch"
HISTORY_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{}/0"
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
OUT = ROOT / "data" / "history"
OUT.mkdir(parents=True, exist_ok=True)


def session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def get_universe():
    s = session()
    r = s.get(MARKET_URL, params=PARAMS, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    rows = r.json().get("marketwatch", [])
    out = {}
    for x in rows:
        code = str(x.get("insCode", "")).strip()
        if code:
            out[code] = {
                "symbol": x.get("lVal18AFC"),
                "name": x.get("lVal30"),
            }
    return out


def fetch_one(item):
    code, meta = item
    s = session()
    url = HISTORY_URL.format(code)
    r = s.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    rows = r.json().get("closingPriceDaily", [])
    if not rows:
        return code, meta, None
    df = pd.DataFrame(rows)
    df["insCode"] = df.get("insCode", code).astype(str)
    df["date"] = pd.to_datetime(df["dEven"].astype(str), format="%Y%m%d", errors="coerce")
    df["symbol"] = meta.get("symbol")
    df["name"] = meta.get("name")
    keep = ["insCode", "symbol", "name", "date", "priceFirst", "priceMax", "priceMin", "pClosing", "qTotTran5J", "qTotCap", "zTotTran", "priceYesterday", "pDrCotVal"]
    keep = [c for c in keep if c in df.columns]
    df = df[keep].sort_values("date")
    df = df.rename(columns={
        "priceFirst": "open",
        "priceMax": "high",
        "priceMin": "low",
        "pClosing": "close",
        "qTotTran5J": "volume",
        "qTotCap": "trade_value",
        "zTotTran": "trade_count",
        "priceYesterday": "prev_close",
        "pDrCotVal": "last",
    })
    return code, meta, df


universe = get_universe()
print(f"UNIVERSE {len(universe)}")
failed = []
count = 0
rows_total = 0

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(fetch_one, item): item[0] for item in universe.items()}
    for fut in concurrent.futures.as_completed(futures):
        code = futures[fut]
        try:
            _, meta, df = fut.result()
            if df is None or df.empty:
                continue
            out = OUT / f"{code}.csv.gz"
            df.to_csv(out, index=False, compression="gzip", encoding="utf-8")
            count += 1
            rows_total += len(df)
            if count % 50 == 0:
                print(f"DONE {count} symbols / {rows_total} rows")
        except Exception as e:
            failed.append({"insCode": code, "error": repr(e)})

(OUT / "failed.json").write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"COMPLETE symbols={count} rows={rows_total} failed={len(failed)}")
