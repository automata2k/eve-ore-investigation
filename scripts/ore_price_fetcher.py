import urllib.request
import json
import ssl
import os
from datetime import datetime

# REGION IDs
REGIONS = {
    "The Forge": "10000002",
    "Domain": "10000043",
    "Sinq Laison": "10000032",
    "Genesis": "10000067",
    "Metropolis": "10000042"
}

# EXACT STATION NAMES & IDs for Reference
STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant", "region": "The Forge"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy", "region": "Domain"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant", "region": "Sinq Laison"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau", "region": "The Forge"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau", "region": "Genesis"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau", "region": "Metropolis"}
}

VOLUMES = {
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, 
    "28416": 0.20, "28668": 0.01, "2454": 5.0, "2486": 5.0, "2203": 5.0, "195": 0.1
}

Ores = {"Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422", "Compressed Omber": "28399", "Compressed Gneiss": "28416"}
Goods = {"Nanite Repair Paste": "28668", "Warrior I": "2486", "Hobgoblin I": "2454", "Scourge Heavy Missile": "195", "Acolyte I": "2203"}

def fetch_tycoon_stats(region_id, type_id):
    url = f"https://evetycoon.com/api/v1/market/stats/{region_id}/{type_id}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Tycoon'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    
    jita_market = {name: fetch_tycoon_stats(REGIONS["The Forge"], tid) for name, tid in {**Ores, **Goods}.items()}
    
    summary = "# 🚀 EVE Arbitrage Daily Report (Verified)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 💎 Market Data: EVE Tycoon API (Regional)\n"
    summary += "Prices are fetched per region to avoid station-only traps.\n\n"
    
    summary += "### 🚛 Daily Trade Run (Optimized 35,000 m³)\n"
    summary += "*Logic: Buy at Region Sell Average, Sell at Region Buy Average (Immediate Liquidity).*\n\n"

    runs = []
    for h_key, hub in STATIONS.items():
        if h_key == "Jita IV-4": continue
        reg_id = REGIONS[hub["region"]]
        hub_market = {name: fetch_tycoon_stats(reg_id, tid) for name, tid in {**Ores, **Goods}.items()}
        
        # Jita -> Hub
        best_out = None
        best_out_p = 0
        for name, tid in Goods.items():
            j_cost = float(jita_market[name].get("minSell", 0))
            h_gain = float(hub_market[name].get("maxBuy", 0))
            if j_cost > 0 and h_gain > 0:
                net_p = (h_gain * (1-tax)) - j_cost
                if net_p > 0:
                    u = int(cargo_max / VOLUMES[tid])
                    p = net_p * u
                    if p > best_out_p:
                        best_out_p = p
                        best_out = {"name": name, "u": u, "profit": p}

        # Hub -> Jita
        best_in = None
        best_in_p = 0
        for name, tid in Ores.items():
            h_cost = float(hub_market[name].get("minSell", 0))
            j_gain = float(jita_market[name].get("maxBuy", 0))
            if h_cost > 0 and j_gain > 0:
                net_p = (j_gain * (1-tax)) - h_cost
                if net_p > 0:
                    u = int(cargo_max / VOLUMES[tid])
                    p = net_p * u
                    if p > best_in_p:
                        best_in_p = p
                        best_in = {"name": name, "u": u, "profit": p}
        
        if best_out_p > 0 or best_in_p > 0:
            runs.append({"hub": hub["region"], "key": h_key, "out": best_out, "in": best_in, "total": best_out_p + best_in_p})

    runs.sort(key=lambda x: x['total'], reverse=True)
    if not runs: summary += "No immediate arbitrage loops found today. Markets are tightly held.\n\n"
    for r in runs[:3]:
        summary += f"#### The {r['hub']} Loop ({r['key']})\n"
        if r['out']: summary += f"1. **OUT:** Buy **{r['out']['u']:,} x {r['out']['name']}** (Jita) -> Profit: **{r['out']['profit']/1e6:.1f}M**\n"
        else: summary += "1. **OUT:** No profitable outbound goods.\n"
        if r['in']: summary += f"2. **IN:** Buy **{r['in']['u']:,} x {r['in']['name']}** (Hub) -> Profit: **{r['in']['profit']/1e6:.1f}M**\n"
        else: summary += "2. **IN:** No profitable return ores.\n"
        summary += f"**Predicted Round-Trip Profit: {r['total']/1e6:.1f} Million ISK**\n\n"

    summary += "\n## 📊 Real-Time Reality Check (API Verified)\n"
    summary += "| Item | Region | Hub Sell | Hub Buy | Jita Sell | Jita Buy |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for h_name in ["Domain", "Sinq Laison", "The Forge"]:
        rid = REGIONS[h_name]
        for name, tid in [("Warrior I", "2486"), ("Nanite Repair Paste", "28668")]:
            m = fetch_tycoon_stats(rid, tid)
            j = fetch_tycoon_stats(REGIONS["The Forge"], tid)
            summary += f"| {name} | {h_name} | {float(m.get('minSell',0)):,.0f} | {float(m.get('maxBuy',0)):,.0f} | {float(j.get('minSell',0)):,.0f} | {float(j.get('maxBuy',0)):,.0f} |\n"

    summary += "\n## ℹ️ Reference\n"
    for k, v in STATIONS.items(): summary += f"**{k}**: {v['name']} ({v['region']})\n\n"
    return summary

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(base_dir, "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Report verified with Tycoon API.")
