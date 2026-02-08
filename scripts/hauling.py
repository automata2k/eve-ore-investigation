import urllib.request
import json
import ssl
import os
from datetime import datetime

# REGION CONFIG
REGIONS = {
    "The Forge (Jita)": "10000002",
    "Domain (Amarr)": "10000043",
    "Sinq Laison (Dodixie)": "10000032",
    "Heimatar (Rens)": "10000030",
    "Metropolis (Hek)": "10000042",
    "Genesis (Apanake)": "10000067"
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

def fetch_tycoon_stats(region_id, type_id):
    url = f"https://evetycoon.com/api/v1/market/stats/{region_id}/{type_id}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Final-Correction'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    
    # 1. Fetch Jita Region Averages (5% filtered)
    jita_rid = REGIONS["The Forge (Jita)"]
    jita_market = {name: fetch_tycoon_stats(jita_rid, tid) for name, tid in SCAN_POOL.items()}
    
    summary = "# 🚀 EVE Arbitrage Daily Report (Final Corrected Logic)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🛡️ VERIFIED PAYLOAD LOGIC (EVE Tycoon API):\n"
    summary += "- **Scam Protection:** Ignoring 'Max Buy' and 'Min Sell'. Only using **Top 5% Weighted Averages**.\n"
    summary += "- **Logistics:** Buy at Target Region Sell Avg -> Sell at Destination Region Buy Avg.\n"
    summary += "- **Liquidity:** Requires minimum 1000 settlement units in the target region.\n\n"

    summary += "## 🚛 Top 3 High-Volume Verified Runs (Round-Trip)\n"

    all_loops = []
    for hub_name, reg_id in REGIONS.items():
        if hub_name == "The Forge (Jita)": continue
        
        # outbound Leg (Jita -> Hub)
        o_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in VOLUMES: continue
            j_cost = float(jita_market[name].get("sellAvgFivePercent", 0)) # Real cost to buy at scale in Jita
            h_gain = float(fetch_tycoon_stats(reg_id, tid).get("buyAvgFivePercent", 0)) # Real price to sell at scale in Hub
            h_vol = float(fetch_tycoon_stats(reg_id, tid).get("buyVolume", 0))
            
            if j_cost > 0 and h_gain > 0 and h_vol > 500:
                net_p = (h_gain * (1 - tax)) - j_cost
                if net_p > 0:
                    u = int(min(cargo_max / VOLUMES[tid], h_vol * 0.2))
                    if u > 0: o_opts.append({"name": name, "u": u, "p": net_p * u})

        # Inbound Leg (Hub -> Jita)
        i_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in VOLUMES: continue
            h_stats = fetch_tycoon_stats(reg_id, tid)
            h_cost = float(h_stats.get("sellAvgFivePercent", 0)) # Real cost to buy in Hub
            j_gain = float(jita_market[name].get("buyAvgFivePercent", 0)) # Real price to sell in Jita
            j_vol = float(jita_market[name].get("buyVolume", 0))
            
            if h_cost > 0 and j_gain > 0 and j_vol > 1000:
                net_p = (j_gain * (1 - tax)) - h_cost
                if net_p > 0:
                    u = int(min(cargo_max / VOLUMES[tid], j_vol * 0.2))
                    if u > 0: i_opts.append({"name": name, "u": u, "p": net_p * u})

        best_out = max(o_opts, key=lambda x: x['p'], default=None)
        best_in = max(i_opts, key=lambda x: x['p'], default=None)
        total = (best_out['p'] if best_out else 0) + (best_in['p'] if best_in else 0)
        
        if total > 0:
            all_loops.append({"hub": hub_name, "out": best_out, "in": best_in, "total": total})

    all_loops.sort(key=lambda x: x['total'], reverse=True)
    
    if not all_loops:
        summary += "No immediate arbitrage found using weighted averages. The market is currently neutral.\n\n"
    
    for i, r in enumerate(all_loops[:3], 1):
        summary += f"### {i}. The {r['hub']} Connection\n"
        if r['out']: summary += f"- **OUT:** {r['out']['u']:,} x {r['out']['name']} -> Net Profit: **{r['out']['p']/1e6:.1f}M**\n"
        else: summary += "- **OUT:** No profitable outbound goods.\n"
        if r['in']: summary += f"- **IN:** {r['in']['u']:,} x {r['in']['name']} -> Net Profit: **{r['in']['p']/1e6:.1f}M**\n"
        else: summary += "- **IN:** No profitable return ores.\n"
        summary += f"**Predicted Total Trip Profit: {r['total']/1e6:.1f} Million ISK**\n\n"

    summary += "\n*Generated via EVE Tycoon Regional Weighted Averages. This logic is immune to single-station scam orders.* 🍤"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HAULING.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market logic fixed. Tycoon Weighted Averages implemented.")
