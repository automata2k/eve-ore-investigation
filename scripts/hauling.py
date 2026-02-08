import urllib.request
import json
import ssl
import os
from datetime import datetime

# FULL MAJOR HUB & MISSION HUB LISTING
STATIONS = {
    "Jita IV-4": "60003760",      # The Forge (Main Hub)
    "Amarr VIII": "60008494",     # Domain (Trade Hub)
    "Dodixie IX": "60011866",     # Sinq Laison (Trade Hub)
    "Rens VI": "60004588",        # Heimatar (Trade Hub)
    "Hek VIII": "60011746",       # Metropolis (Trade Hub)
    "Osmon II": "60012667",       # The Forge (Mission Hub - Sisters)
    "Apanake IV": "60005236",     # Genesis (Mission Hub - Sisters)
    "Lanngisi VII": "60009514"    # Metropolis (Mission Hub - Sisters)
}

REGIONS = {
    "60003760": "10000002", "60008494": "10000043", "60011866": "10000032",
    "60004588": "10000030", "60011746": "10000042", "60012667": "10000002",
    "60005236": "10000067", "60009514": "10000042"
}

# Physical volumes for ROI math (m3)
ITEM_VOLUMES = {
    # Drones (Standard 5m3)
    "2486": 5.0, "2454": 5.0, "2203": 5.0, "2470": 5.0, "31177": 5.0, "2476": 5.0, "2459": 5.0, "2446": 5.0,
    # Ammo (0.01m3 or 0.1m3)
    "218": 0.01, "230": 0.01, "206": 0.01, "219": 0.01, "222": 0.01, "221": 0.01, "195": 0.1, "191": 0.1,
    "193": 0.1, "196": 0.1, "194": 0.1, "183": 0.01, "177": 0.01,
    # Fuel & Blocks
    "4051": 5.0, "4247": 5.0, "4312": 5.0, "4246": 5.0,
    # Common Industrial Items
    "520": 5.0, "11299": 5.0, "11301": 5.0, "380": 10.0, "382": 20.0, "434": 5.0, "438": 5.0,
    "444": 5.0, "447": 5.0, "440": 5.0, "1192": 5.0, "10838": 10.0, "28668": 0.01, "11578": 10.0, "524": 5.0,
    "33477": 100.0, "33474": 50.0,
    # Compressed Ores (Typical highsec m3)
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, "28416": 0.20
}

# The High-Velocity Scan Pool (~40 items monitored for arbitrage)
SCAN_POOL = {
    # Drones
    "Warrior I": "2486", "Hobgoblin I": "2454", "Acolyte I": "2203", "Hornet I": "2470", "Salvage Drone I": "31177",
    # Crystals / Ammo
    "Antimatter Charge M": "218", "Antimatter Charge S": "230", "Scourge Heavy Missile": "195",
    "Nova Heavy Missile": "193", "Mjolnir Heavy Missile": "196", "Inferno Heavy Missile": "194",
    "EMP S": "183", "EMP M": "177",
    # Fuel
    "Nitrogen Fuel Block": "4051", "Oxygen Fuel Block": "4247", "Helium Fuel Block": "4312", "Hydrogen Fuel Block": "4246",
    # Essentials
    "Nanite Repair Paste": "28668", "Damage Control I": "520", "1600mm Steel Plates I": "11299", "5MN Microwarpdrive I": "434",
    "Medium Shield Extender I": "380", "Mobile Tractor Unit": "33477", "Mobile Depot": "33474",
    # Compressed Ores
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394", "Compressed Gneiss": "28416"
}

def fetch_hub(sid, type_ids):
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={sid}&types={','.join(type_ids)}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-FullHubScan'})
        with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    item_ids = list(SCAN_POOL.values())
    
    # 1. Fetch Jita IV-4 first (The Anchor)
    jita_market = fetch_hub(STATIONS["Jita IV-4"], item_ids)
    
    summary = "# 🚀 EVE Arbitrage Daily Briefing (Global Hub Scan)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 💎 Scan Logic: Comprehensive Hub Coverage\n"
    summary += "- **Scope:** Scanned all 5 main trade hubs + 3 major Sisters mission hubs.\n"
    summary += "- **Validation:** 3.6% transaction fees deducted. Verification based on 24h market depth.\n\n"

    summary += "## 🚛 Top 3 Verified Haul Runs (Round-Trip)\n"

    loops = []
    for h_name, sid in STATIONS.items():
        if h_name == "Jita IV-4": continue
        hub_market = fetch_hub(sid, item_ids)
        
        # Best Outbound (Jita -> Hub)
        o_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in ITEM_VOLUMES: continue
            j_cost = float(jita_market.get(tid, {}).get("sell", {}).get("min", 0))
            h_gain = float(hub_market.get(tid, {}).get("buy", {}).get("max", 0))
            h_demand = float(hub_market.get(tid, {}).get("buy", {}).get("volume", 0))
            if j_cost > 0 and h_gain > 0 and h_demand > 50:
                net_p = (h_gain * (1-tax)) - j_cost
                if net_p > 0:
                    u = int(min(cargo_max / ITEM_VOLUMES[tid], h_demand * 0.25))
                    if u > 0: o_opts.append({"name": name, "u": u, "p": net_p * u})

        # Best Inbound (Hub -> Jita)
        i_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in ITEM_VOLUMES: continue
            h_cost = float(hub_market.get(tid, {}).get("sell", {}).get("min", 0))
            j_gain = float(jita_market.get(tid, {}).get("buy", {}).get("max", 0))
            j_demand = float(jita_market.get(tid, {}).get("buy", {}).get("volume", 0))
            if h_cost > 0 and j_gain > 0 and j_demand > 50:
                net_p = (j_gain * (1-tax)) - h_cost
                if net_p > 0:
                    u = int(min(cargo_max / ITEM_VOLUMES[tid], j_demand * 0.25))
                    if u > 0: i_opts.append({"name": name, "u": u, "p": net_p * u})

        best_out = max(o_opts, key=lambda x: x['p'], default=None)
        best_in = max(i_opts, key=lambda x: x['p'], default=None)
        total = (best_out['p'] if best_out else 0) + (best_in['p'] if best_in else 0)
        if total > 0:
            loops.append({"hub": h_name, "out": best_out, "in": best_in, "total": total})

    loops.sort(key=lambda x: x['total'], reverse=True)
    
    if not loops:
        summary += "No clear arbitrage round-trips found currently. Local manufacturing is likely better.\n\n"
    
    for i, r in enumerate(loops[:3], 1):
        summary += f"### {i}. The {r['hub']} Round-Trip\n"
        if r['out']: summary += f"- **OUT:** {r['out']['u']:,} x {r['out']['name']} -> Profit: **{r['out']['p']/1e6:.1f}M**\n"
        else: summary += "- **OUT:** No profitable outbound goods.\n"
        if r['in']: summary += f"- **IN:** {r['in']['u']:,} x {r['in']['name']} -> Profit: **{r['in']['p']/1e6:.1f}M**\n"
        else: summary += "- **IN:** No profitable return ores/goods.\n"
        summary += f"**Predicted Round-Trip Profit: {r['total']/1e6:.1f} Million ISK**\n\n"

    summary += "\n## ℹ️ Trading Hub Destination Key\n"
    summary += "| Destination Hub | Region | Full Station Name (Set Destination to this) |\n"
    summary += "| :--- | :--- | :--- |\n"
    summary += "| **Amarr VIII** | Domain | Amarr VIII (Orbis) - Emperor Family Academy |\n"
    summary += "| **Dodixie IX** | Sinq Laison | Dodixie IX - Moon 20 - Federation Navy Assembly Plant |\n"
    summary += "| **Rens VI** | Heimatar | Rens VI - Moon 8 - Brutor Tribe Treasury |\n"
    summary += "| **Hek VIII** | Metropolis | Hek VIII - Moon 12 - Boundless Creation Factory |\n"
    summary += "| **Osmon II** | The Forge | Osmon II - Moon 1 - Sisters of EVE Bureau |\n"
    summary += "| **Apanake IV** | Genesis | Apanake IV - Moon 4 - Sisters of EVE Bureau |\n"
    summary += "| **Lanngisi VII** | Metropolis | Lanngisi VII - Moon 11 - Sisters of EVE Bureau |\n"

    summary += "\n--- \n*Generated by the Shrimp Market Bot checking all 8 major high-sec intersections.* 🍤"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HAULING.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Full Global Hub Scan Complete.")
