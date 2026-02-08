import urllib.request
import json
import ssl
import os
from datetime import datetime

# EXACT STATION CONFIG
STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant", "region_id": "10000002"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy", "region_id": "10000043"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant", "region_id": "10000032"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau", "region_id": "10000002"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau", "region_id": "10000067"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau", "region_id": "10000042"}
}

# ITEM CONFIG
# (Ores use m3 from EVE DB, Goods use standard m3)
VOLUMES = {
    # Ores
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, "28416": 0.20,
    # Drones
    "2486": 5.0, "2454": 5.0, "2203": 5.0, "2470": 5.0,
    # Ammo
    "218": 0.01, "230": 0.01, "206": 0.01, "195": 0.1, "193": 0.1, "196": 0.1, "194": 0.1,
    # Fuel & Modules
    "4051": 5.0, "4247": 5.0, "4312": 5.0, "4246": 5.0, "520": 5.0, "11299": 5.0, "380": 10.0, "434": 5.0,
    "28668": 0.01, "11578": 10.0, "524": 5.0, "33477": 100.0, "33474": 50.0
}

ITEMS = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Omber": "28399", "Compressed Kernite": "28394", "Compressed Gneiss": "28416",
    "Warrior I": "2486", "Hobgoblin I": "2454", "Acolyte I": "2203", "Hornet I": "2470",
    "Nitrogen Fuel Block": "4051", "Oxygen Fuel Block": "4247", "Helium Fuel Block": "4312", 
    "Hydrogen Fuel Block": "4246", "Nanite Repair Paste": "28668", "Mobile Tractor Unit": "33477",
    "Mobile Depot": "33474", "Antimatter Charge M": "218", "Scourge Heavy Missile": "195",
    "Nova Heavy Missile": "193", "Damage Control I": "520", "1600mm Steel Plates I": "11299"
}

def fetch_station(sid, tids):
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={sid}&types={','.join(set(tids))}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Expert'})
        with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read().decode())
    except: return {}

def fetch_region_vol(rid, tid):
    # Used for Vibe check (Liquidity)
    url = f"https://evetycoon.com/api/v1/market/stats/{rid}/{tid}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Liquidity'})
        with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    item_ids = list(ITEMS.values())
    
    # 1. Fetch Station-level exact prices
    jita_st = fetch_station(STATIONS["Jita IV-4"]["id"], item_ids)
    hub_data = {h: fetch_station(STATIONS[h]["id"], item_ids) for h in STATIONS if h != "Jita IV-4"}
    
    summary = "# 🚀 EVE Arbitrage Daily Briefing (Tayra Optimized)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🛡️ Logistics Policy & Corrected Verification\n"
    summary += "- **Source:** Jita IV-4 (The Forge) Station Prices.\n"
    summary += "- **Logic:** Buy at Hub/Jita **Sell Order Min** -> Sell at Hub/Jita **Buy Order Max**.\n"
    summary += "- **Profit:** Realized net income after 3.6% transaction fees.\n\n"
    
    summary += "## 🚛 Top 3 High-Volume Trade Loops\n"
    
    all_loops = []
    for h_key, hub_prices in hub_data.items():
        hub_info = STATIONS[h_key]
        reg_id = hub_info["region_id"]
        
        out_opts = [] # Jita -> Hub
        in_opts = []  # Hub -> Jita
        
        for name, tid in ITEMS.items():
            # OUTBOUND Logic
            j_cost = float(jita_st.get(tid, {}).get("sell", {}).get("min", 0))
            h_gain = float(hub_prices.get(tid, {}).get("buy", {}).get("max", 0))
            h_demand = float(hub_prices.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if j_cost > 0 and h_gain > 0 and h_demand > 5:
                net_p = (h_gain * (1-tax)) - j_cost
                if net_p > 0:
                    u = int(min(cargo_max / VOLUMES[tid], h_demand * 0.3)) # Cap at 30% of current station demand
                    if u > 0: out_opts.append({"name": name, "u": u, "p": net_p * u})

            # INBOUND Logic
            h_cost = float(hub_prices.get(tid, {}).get("sell", {}).get("min", 0))
            j_gain = float(jita_st.get(tid, {}).get("buy", {}).get("max", 0))
            j_demand = float(jita_st.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if h_cost > 0 and j_gain > 0 and j_demand > 5:
                net_p = (j_gain * (1-tax)) - h_cost
                if net_p > 0:
                    u = int(min(cargo_max / VOLUMES[tid], j_demand * 0.3))
                    if u > 0: in_opts.append({"name": name, "u": u, "p": net_p * u})

        best_out = max(out_opts, key=lambda x: x['p'], default=None)
        best_in = max(in_opts, key=lambda x: x['p'], default=None)
        total = (best_out['p'] if best_out else 0) + (best_in['p'] if best_in else 0)
        
        if total > 0:
            all_loops.append({"key": h_key, "out": best_out, "in": best_in, "total": total})

    all_loops.sort(key=lambda x: x['total'], reverse=True)
    
    if not all_loops:
        summary += "No immediate arbitrage loops found for current station buy orders.\n\n"
    
    for i, r in enumerate(all_loops[:3], 1):
        summary += f"### {i}. The {r['key']} Connection\n"
        if r['out']: summary += f"- **OUT:** {r['out']['u']:,} x {r['out']['name']} (Jita -> {r['key']}) -> Profit: **{r['out']['p']/1e6:.1f}M**\n"
        else: summary += "- **OUT:** No station-specific Jita->Hub arbitrage.\n"
        if r['in']: summary += f"- **IN:** {r['in']['u']:,} x {r['in']['name']} ({r['key']} -> Jita) -> Profit: **{r['in']['p']/1e6:.1f}M**\n"
        else: summary += "- **IN:** No station-specific Hub->Jita arbitrage.\n"
        summary += f"**Predicted Round-Trip Profit: {r['total']/1e6:,.1f} Million ISK**\n\n"

    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Loops Refreshed with Station-Specific Data.")
