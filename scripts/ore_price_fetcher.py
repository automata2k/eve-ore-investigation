import urllib.request
import json
import ssl
import os
from datetime import datetime

# HUB SETTINGS
STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant", "region": "The Forge"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy", "region": "Domain"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant", "region": "Sinq Laison"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau", "region": "The Forge"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau", "region": "Genesis"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau", "region": "Metropolis"}
}

# ITEM VOLUMES (m3) - COMPREHENSIVE
VOLUMES = {
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, 
    "28404": 0.20, "28407": 0.20, "28410": 0.20, "28416": 0.20, "28415": 0.20, "28418": 0.20,
    "17466": 0.20, "28419": 0.20, "28420": 0.20,
    "195": 0.1, "196": 0.1, "191": 0.1, "193": 0.1, "194": 0.1,
    "28668": 0.01, "2454": 5.0, "2486": 5.0, "2203": 5.0, "218": 0.01
}

# ITEM DEFINITIONS
Ores = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394",
    "Compressed Gneiss": "28416", "Compressed Jaspet": "28404", "Compressed Hemorphite": "28407",
    "Compressed Hedbergite": "28410", "Compressed Dark Ochre": "28415", "Compressed Spodumain": "17466"
}

Goods = {
    "Nanite Repair Paste": "28668", "Warrior I": "2486", "Hobgoblin I": "2454", 
    "Scourge Heavy Missile": "195", "Acolyte I": "2203", "Nova Heavy Missile": "193",
    "Mjolnir Heavy Missile": "196", "Inferno Heavy Missile": "194"
}

def fetch(sid, tids):
    # DYNAMIC FETCH: Ensures real prices from API every time
    tids_clean = [str(t) for t in tids if t]
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={sid}&types={','.join(set(tids_clean))}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-LiveFetch-Refilled'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"API Error at station {sid}: {e}")
        return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    all_ids = list(Ores.values()) + list(Goods.values())
    
    # LIVE API CALLS
    jita = fetch(STATIONS["Jita IV-4"]["id"], all_ids)
    hub_data = {h: fetch(STATIONS[h]["id"], all_ids) for h in STATIONS if h != "Jita IV-4"}

    summary = "# 🚀 EVE Arbitrage Daily Report\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🚛 Daily Trade Run (Optimized 35,000 m³)\n"
    summary += "*Verified via Live API. Profit includes 3.6% fees. Inbound legs are now explicitly tracked everywhere.*\n\n"

    runs = []
    for h_key, h_mkt in hub_data.items():
        # OUT (Jita -> Hub)
        best_out = None
        best_out_p = 0
        for name, tid in Goods.items():
            j_cost = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
            h_price = float(h_mkt.get(tid, {}).get("sell", {}).get("min", 0))
            h_vol = float(h_mkt.get(tid, {}).get("sell", {}).get("volume", 0))
            
            if j_cost > 0 and h_price > j_cost and h_vol > 20:
                net_p = (h_price * (1-tax)) - j_cost
                if net_p > 0:
                    u = int(min(cargo_max / VOLUMES[tid], h_vol * 0.3)) # Cap at 30% of hub stock
                    p = net_p * u
                    if p > best_out_p:
                        best_out_p = p
                        best_out = {"name": name, "u": u, "profit": p, "cost": j_cost * u}

        # IN (Hub -> Jita)
        best_in = None
        best_in_p = 0
        for name, tid in Ores.items():
            h_cost = float(h_mkt.get(tid, {}).get("sell", {}).get("min", 0))
            j_price = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
            j_vol = float(jita.get(tid, {}).get("sell", {}).get("volume", 0))
            
            if h_cost > 0 and j_price > h_cost:
                net_p = (j_price * (1-tax)) - h_cost
                if net_p > 0:
                    u = int(min(cargo_max / VOLUMES[tid], j_vol * 0.2)) # Cap at 20% Jita depth
                    p = net_p * u
                    if p > best_in_p:
                        best_in_p = p
                        best_in = {"name": name, "u": u, "profit": p, "cost": h_cost * u}
        
        runs.append({"hub": h_key, "out": best_out, "in": best_in, "total": max(0, best_out_p) + max(0, best_in_p)})

    runs.sort(key=lambda x: x['total'], reverse=True)
    
    for r in runs[:4]: # Show more loops to ensure Osmon/Lanngisi variety
        hub_name = r['hub']
        summary += f"#### The {STATIONS[hub_name]['region']} Loop ({hub_name})\n"
        # Explicit Step tracking
        if r['out']:
            summary += f"1. **OUTBOUND:** Buy **{r['out']['u']:,} x {r['out']['name']}** (Jita) -> Profit: **{r['out']['profit']/1e6:.2f}M**\n"
        else:
            summary += f"1. **OUTBOUND:** No profitable manufactured goods found for this leg today.\n"
            
        if r['in']:
            summary += f"2. **INBOUND:** Buy **{r['in']['u']:,} x {r['in']['name']}** ({hub_name}) -> Profit: **{r['in']['profit']/1e6:.2f}M**\n"
        else:
            summary += f"2. **INBOUND:** No profitable ore spreads found for the return leg.\n"
            
        summary += f"**Predicted Total Trip Profit: {r['total']/1e6:.2f} Million ISK**\n\n"

    summary += "\n## ℹ️ Reference\n"
    for k, v in STATIONS.items(): summary += f"**{k}**: {v['name']} ({v['region']})\n\n"
    return summary

if __name__ == "__main__":
    import sys
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(base_dir, "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Data Refresh Complete.")
