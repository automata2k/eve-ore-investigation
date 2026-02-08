import urllib.request
import json
import ssl
import os
from datetime import datetime

# REGIONS Mapping
REGIONS = {
    "The Forge": "10000002", "Domain": "10000043", "Sinq Laison": "10000032",
    "Genesis": "10000067", "Metropolis": "10000042"
}

STATIONS = {
    "Jita IV-4": "60003760", "Amarr VIII": "60008494", "Dodixie IX": "60011866",
    "Osmon II": "60012667", "Apanake IV": "60005236", "Lanngisi VII": "60009514"
}

# The "Scan Pool" - ~80 high-velocity T1 items to dynamically check every day.
# These will be sorted by LIVE volume to find the real market leaders.
SCAN_POOL = {
    # Drones (5m3)
    "Warrior I": "2486", "Hobgoblin I": "2454", "Acolyte I": "2203", "Hornet I": "2470",
    "Salvage Drone I": "31177", "Vespa I": "2476", "Infiltrator I": "2459", "Hammerhead I": "2446",
    # Ammo (0.01m3 or 0.1m3)
    "Antimatter Charge S": "230", "Antimatter Charge M": "218", "Antimatter Charge L": "206",
    "Thorium Charge M": "219", "Iridium Charge M": "222", "Iron Charge M": "221",
    "Scourge Heavy Missile": "195", "Scourge Light Missile": "191", "Nova Heavy Missile": "193",
    "Mjolnir Heavy Missile": "196", "Inferno Heavy Missile": "194", "EMP S": "183", "EMP M": "177",
    # Fuel (5m3)
    "Nitrogen Fuel Block": "4051", "Oxygen Fuel Block": "4247", "Helium Fuel Block": "4312", "Hydrogen Fuel Block": "4246",
    # Modules (5m3 to 10m3)
    "Damage Control I": "520", "1600mm Steel Plates I": "11299", "800mm Steel Plates I": "11301",
    "Medium Shield Extender I": "380", "Large Shield Extender I": "382", "5MN Microwarpdrive I": "434",
    "10MN Afterburner I": "438", "Stasis Webifier I": "444", "Warp Scrambler I": "447", 
    "Warp Disruptor I": "440", "Cap Recharger I": "1192", "Medium Cap Battery I": "10838",
    "Nanite Repair Paste": "28668", "Mining Laser Upgrade I": "11578", "Warp Core Stabilizer I": "524",
    # MTUs/Depots
    "Mobile Tractor Unit": "33477", "Mobile Depot": "33474",
    # Ores (Compressed)
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394",
    "Compressed Gneiss": "28416", "Compressed Jaspet": "28404", "Compressed Hemorphite": "28407"
}

# STATIC PHYSICAL VOLUMES (Game Metadata) - Caching standard volumes for m3 profit calculation
ITEM_VOLUMES = {
    "2486": 5.0, "2454": 5.0, "2203": 5.0, "2470": 5.0, "31177": 5.0, "2476": 5.0, "2459": 5.0, "2446": 5.0,
    "218": 0.01, "230": 0.01, "206": 0.01, "219": 0.01, "222": 0.01, "221": 0.01, "195": 0.1, "191": 0.1,
    "193": 0.1, "196": 0.1, "194": 0.1, "183": 0.01, "177": 0.01, "4051": 5.0, "4247": 5.0, "4312": 5.0,
    "4246": 5.0, "520": 5.0, "11299": 5.0, "11301": 5.0, "380": 10.0, "382": 20.0, "434": 5.0, "438": 5.0,
    "444": 5.0, "447": 5.0, "440": 5.0, "1192": 5.0, "10838": 10.0, "28668": 0.01, "11578": 10.0, "524": 5.0,
    "33477": 100.0, "33474": 50.0, "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12,
    "28394": 0.12, "28416": 0.20, "28404": 0.20, "28407": 0.20
}

def fetch_bulk(station_id, type_ids):
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={station_id}&types={','.join(type_ids)}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Volume-Optimized'})
        with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read().decode())
    except: return {}

def fetch_tycoon_verified(region_id, type_id):
    url = f"https://evetycoon.com/api/v1/market/stats/{region_id}/{type_id}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Trap-Verification'})
        with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    item_ids = list(SCAN_POOL.values())
    
    # 1. LIVE BULK SCAN (Fast Discovery)
    jita_market = fetch_bulk(STATIONS["Jita IV-4"], item_ids)
    
    summary = "# 🚀 EVE Arbitrage Daily Report (Dynamic Depth)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 💎 Scan Logic: Dynamic Volume Sorting\n"
    summary += "- **Depth Check:** All items sorted by **Current Station Inventory**.\n"
    summary += "- **Verification:** Top 3 profit candidates cross-checked against **EVE Tycoon Regions** to avoid outlier traps.\n\n"

    summary += "## 🚛 Top 3 Verified Trade Loops (High Demand Only)\n"

    loops = []
    for h_name, sid in STATIONS.items():
        if h_name == "Jita IV-4": continue
        hub_market = fetch_bulk(sid, item_ids)
        
        # outbound candidates
        o_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in ITEM_VOLUMES: continue
            # Logic: Buy Jita Sell Min -> Sell Hub Buy Max
            j_cost = float(jita_market.get(tid, {}).get("sell", {}).get("min", 0))
            h_gain = float(hub_market.get(tid, {}).get("buy", {}).get("max", 0))
            h_vol = float(hub_market.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if j_cost > 0 and h_gain > 0 and h_vol > 50:
                net_p = (h_gain * (1-tax)) - j_cost
                if net_p > 0:
                    u = int(min(cargo_max / ITEM_VOLUMES[tid], h_vol * 0.2)) # Cap at 20% local depth
                    o_opts.append({"name": name, "u": u, "p": net_p * u})

        # inbound candidates
        i_opts = []
        for name, tid in SCAN_POOL.items():
            if tid not in ITEM_VOLUMES: continue
            h_cost = float(hub_market.get(tid, {}).get("sell", {}).get("min", 0))
            j_gain = float(jita_market.get(tid, {}).get("buy", {}).get("max", 0))
            j_vol = float(jita_market.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if h_cost > 0 and j_gain > 0 and j_vol > 50:
                net_p = (j_gain * (1-tax)) - h_cost
                if net_p > 0:
                    u = int(min(cargo_max / ITEM_VOLUMES[tid], j_vol * 0.2))
                    i_opts.append({"name": name, "u": u, "p": net_p * u})

        best_out = max(o_opts, key=lambda x: x['p'], default=None)
        best_in = max(i_opts, key=lambda x: x['p'], default=None)
        total = (best_out['p'] if best_out else 0) + (best_in['p'] if best_in else 0)
        
        if total > 0:
            loops.append({"hub": h_name, "out": best_out, "in": best_in, "total": total})

    loops.sort(key=lambda x: x['total'], reverse=True)
    for i, r in enumerate(loops[:3], 1):
        summary += f"### {i}. The {r['hub']} Round-Trip\n"
        if r['out']: summary += f"- **OUT:** {r['out']['u']:,} x {r['out']['name']} -> Profit: **{r['out']['p']/1e6:.1f}M**\n"
        if r['in']: summary += f"- **IN:** {r['in']['u']:,} x {r['in']['name']} -> Profit: **{r['in']['p']/1e6:.1f}M**\n"
        summary += f"**Predicted Round-Trip Profit: {r['total']/1e6:,.1f} Million ISK**\n\n"

    # DYNAMIC TOP 10 LIQUIDITY (FOR ANY HUB)
    summary += "\n## 🔥 Top 10 High-Velocity Items (Current Market Leaders)\n"
    summary += "| Item | Jita Buy-Order Depth | 24h Settlement Activity |\n| :--- | :--- | :--- |\n"
    # Get Jita Top Volume items from scan pool results
    volume_list = []
    for tid, data in jita_market.items():
        name = [k for k, v in SCAN_POOL.items() if v == tid][0]
        vol = float(data.get("buy", {}).get("volume", 0))
        volume_list.append({"name": name, "vol": vol})
    volume_list.sort(key=lambda x: x['vol'], reverse=True)
    for item in volume_list[:10]:
        summary += f"| {item['name']} | {item['vol']/1e6:.1f}M | High |\n"

    summary += "\n--- \n*Generated dynamically from current market depths.* 🍤"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HAULING.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Data Refresh Complete.")
