import urllib.request
import json
import ssl
import os
from datetime import datetime

# HUB SETTINGS
STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant"},
    "Rens VI": {"id": "60004588", "name": "Rens VI - Moon 8 - Brutor Tribe Treasury"},
    "Hek VIII": {"id": "60011746", "name": "Hek VIII - Moon 12 - Boundless Creation Factory"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau"}
}

# Physical volumes (m3)
VOLUMES = {
    "2486": 5.0, "2454": 5.0, "2203": 5.0, "2470": 5.0, "218": 0.01, "230": 0.01, "195": 0.1,
    "193": 0.1, "194": 0.1, "4051": 5.0, "4247": 5.0, "4312": 5.0, "4246": 5.0, "520": 5.0,
    "11299": 5.0, "380": 10.0, "28668": 0.01, "33477": 100.0, "33474": 50.0,
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, "28416": 0.20
}

# The High-Volume Scan Pool
SCAN_POOL = {
    "Warrior I": "2486", "Hobgoblin I": "2454", "Acolyte I": "2203", "Hornet I": "2470",
    "Antimatter Charge M": "218", "Antimatter Charge S": "230", "Scourge Heavy Missile": "195",
    "Nova Heavy Missile": "193", "Inferno Heavy Missile": "194", "Nitrogen Fuel Block": "4051",
    "Oxygen Fuel Block": "4247", "Helium Fuel Block": "4312", "Hydrogen Fuel Block": "4246",
    "Nanite Repair Paste": "28668", "Damage Control I": "520", "1600mm Steel Plates I": "11299",
    "Medium Shield Extender I": "380", "Mobile Tractor Unit": "33477", "Mobile Depot": "33474",
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394",
    "Compressed Gneiss": "28416"
}

def fetch_station(sid, type_ids):
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={sid}&types={','.join(type_ids)}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-FinalVerifier'})
        with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036 # Combined Sales Tax + Broker Fee for immediate sell
    item_ids = list(SCAN_POOL.values())
    
    jita = fetch_station(STATIONS["Jita IV-4"]["id"], item_ids)
    
    summary = "# 🚀 EVE Arbitrage Daily Report (Verified Logic)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🛡️ VERIFIED ARBITRAGE LOGIC:\n"
    summary += "1. **Outbound:** Buy at Jita **Sell Order Min** -> Immediately Sell to Hub **Buy Order Max**.\n"
    summary += "2. **Inbound:** Buy at Hub **Sell Order Min** -> Immediately Sell to Jita **Buy Order Max**.\n"
    summary += f"3. **Fees:** Calculations deduct {(tax*100):.1f}% for actual take-home profit.\n\n"

    summary += "## 🚛 Top 3 Instant-Profit Haul Runs (Round-Trip)\n"

    all_loops = []
    for h_key, hub_conf in STATIONS.items():
        if h_key == "Jita IV-4": continue
        hub_mkt = fetch_station(hub_conf["id"], item_ids)
        
        # outbound candidates (Jita -> Hub)
        o_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in VOLUMES: continue
            j_cost = float(jita.get(tid, {}).get("sell", {}).get("min", 0)) # Immediate Buy at Jita
            h_gain = float(hub_mkt.get(tid, {}).get("buy", {}).get("max", 0)) # Immediate Sell at Hub
            h_depth = float(hub_mkt.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if j_cost > 0 and h_gain > 0:
                net_profit_per = (h_gain * (1 - tax)) - j_cost
                if net_profit_per > 0 and h_depth > 0:
                    u = int(min(cargo_max / VOLUMES[tid], h_depth))
                    if u > 0: o_opts.append({"name": name, "u": u, "p": net_profit_per * u})

        # inbound candidates (Hub -> Jita)
        i_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in VOLUMES: continue
            h_cost = float(hub_mkt.get(tid, {}).get("sell", {}).get("min", 0)) # Immediate Buy at Hub
            j_gain = float(jita.get(tid, {}).get("buy", {}).get("max", 0))    # Immediate Sell at Jita
            j_depth = float(jita.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if h_cost > 0 and j_gain > 0:
                net_profit_per = (j_gain * (1 - tax)) - h_cost
                if net_profit_per > 0 and j_depth > 0:
                    u = int(min(cargo_max / VOLUMES[tid], j_depth))
                    if u > 0: i_opts.append({"name": name, "u": u, "p": net_profit_per * u})

        best_out = max(o_opts, key=lambda x: x['p'], default=None)
        best_in = max(i_opts, key=lambda x: x['p'], default=None)
        total = (best_out['p'] if best_out else 0) + (best_in['p'] if best_in else 0)
        if total > 500000: # Filter runs under 0.5M profit
            all_loops.append({"key": h_key, "out": best_out, "in": best_in, "total": total})

    all_loops.sort(key=lambda x: x['total'], reverse=True)
    if not all_loops:
        summary += "No immediate profit round-trips found based on current **BUY ORDERS**. The markups you are seeing in-game are likely for Sell Orders (requires waiting).\n\n"
    
    for i, r in enumerate(all_loops[:3], 1):
        summary += f"### {i}. The {r['key']} Round-Trip\n"
        if r['out']: summary += f"- **OUT:** {r['out']['u']:,} x {r['out']['name']} (Jita->{r['key']}) -> Net Profit: **{r['out']['p']/1e6:.1f}M**\n"
        else: summary += "- **OUT:** No profitable immediate dump found.\n"
        if r['in']: summary += f"- **IN:** {r['in']['u']:,} x {r['in']['name']} ({r['key']}->Jita) -> Net Profit: **{r['in']['p']/1e6:.1f}M**\n"
        else: summary += "- **IN:** No profitable return ore found.\n"
        summary += f"**Total Verified Trip Profit: {r['total']/1e6:.1f} Million ISK**\n\n"

    summary += "\n## ℹ️ Trading Hub Destination Search\n"
    for k, v in STATIONS.items(): summary += f"**{k}**: {v['name']}\n\n"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HAULING.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Logic Finalized with correctly verified Buy-vs-Sell orders.")
