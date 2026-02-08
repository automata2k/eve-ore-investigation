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

STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant", "region": "The Forge"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy", "region": "Domain"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant", "region": "Sinq Laison"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau", "region": "The Forge"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau", "region": "Genesis"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau", "region": "Metropolis"}
}

# ITEM IDs & VOLUMES (m3)
VOLUMES = {
    # Ores
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, "28416": 0.20,
    # Drones
    "2486": 5.0, "2454": 5.0, "2203": 5.0, "2470": 5.0,
    # Ammo (Small/Medium/Large)
    "218": 0.01, "230": 0.01, "206": 0.01, "195": 0.1, "193": 0.1, "196": 0.1, "194": 0.1,
    "183": 0.01, "177": 0.01, "165": 0.01,
    # Fuel
    "4051": 5.0, "4247": 5.0, "4312": 5.0, "4246": 5.0,
    # Modules
    "520": 5.0, "11299": 5.0, "380": 10.0, "434": 5.0, "438": 5.0, "28668": 0.01, "11578": 10.0, "524": 5.0,
    # MTU/Depot
    "33477": 100.0, "33474": 50.0
}

ITEMS_TO_SCAN = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394",
    "Compressed Gneiss": "28416", "Warrior I": "2486", "Hobgoblin I": "2454", "Acolyte I": "2203", 
    "Hornet I": "2470", "Antimatter Charge M": "218", "Scourge Heavy Missile": "195",
    "Nova Heavy Missile": "193", "Mjolnir Heavy Missile": "196", "Inferno Heavy Missile": "194",
    "Nitrogen Fuel Block": "4051", "Oxygen Fuel Block": "4247", "Helium Fuel Block": "4312", 
    "Hydrogen Fuel Block": "4246", "Damage Control I": "520", "1600mm Steel Plates I": "11299", 
    "Medium Shield Extender I": "380", "5MN Microwarpdrive I": "434", "10MN Afterburner I": "438", 
    "Nanite Repair Paste": "28668", "Mining Laser Upgrade I": "11578", "Warp Core Stabilizer I": "524",
    "Mobile Tractor Unit": "33477", "Mobile Depot": "33474"
}

def fetch_tycoon_stats(region_id, type_id):
    url = f"https://evetycoon.com/api/v1/market/stats/{region_id}/{type_id}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Final-v1'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    
    # 1. Fetch Jita (The Forge) for everything
    jita_data = {name: fetch_tycoon_stats(REGIONS["The Forge"], tid) for name, tid in ITEMS_TO_SCAN.items()}
    
    # 2. Fetch all other regions
    regional_data = {}
    for r_name in ["Domain", "Sinq Laison", "Genesis", "Metropolis", "The Forge"]:
        regional_data[r_name] = {name: fetch_tycoon_stats(REGIONS[r_name], tid) for name, tid in ITEMS_TO_SCAN.items()}
        
    summary = "# 🚀 EVE Arbitrage Daily Briefing (Tayra Optimized)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🛡️ Logistics Policy\n"
    summary += "- Buy from **Sell Orders** (Immediate Cost) -> Dump into **Buy Orders** (Immediate ISK).\n"
    summary += "- Profits shown are **Net** (3.6% fees deducted).\n"
    summary += "- Recommendations capped at **20% of destination buy-order depth**.\n\n"
    
    summary += "## 🚛 Top 3 High-Volume Trade Loops\n"
    
    all_potential_loops = []
    for h_key, hub in STATIONS.items():
        if h_key == "Jita IV-4": continue
        r_name = hub["region"]
        h_mkt = regional_data[r_name]
        
        # outbound: Jita -> Hub
        leg1_options = []
        for name, tid in ITEMS_TO_SCAN.items():
            j_cost = float(jita_data[name].get("minSell", 0))
            h_price = float(h_mkt[name].get("maxBuy", 0))
            h_demand = float(h_mkt[name].get("buyVolume", 0))
            
            if j_cost > 0 and h_price > j_cost and h_demand > 10:
                net_profit_per = (h_price * (1-tax)) - j_cost
                if net_profit_per > 0:
                    u = int(min(cargo_max / VOLUMES[tid], h_demand * 0.2))
                    if u > 0: leg1_options.append({"name": name, "u": u, "p": net_profit_per * u})

        # inbound: Hub -> Jita
        leg2_options = []
        for name, tid in ITEMS_TO_SCAN.items():
            h_cost = float(h_mkt[name].get("minSell", 0))
            j_price = float(jita_data[name].get("maxBuy", 0))
            j_demand = float(jita_data[name].get("buyVolume", 0))
            
            if h_cost > 0 and j_price > h_cost and j_demand > 10:
                net_profit_per = (j_price * (1-tax)) - h_cost
                if net_profit_per > 0:
                    u = int(min(cargo_max / VOLUMES[tid], j_demand * 0.2))
                    if u > 0: leg2_options.append({"name": name, "u": u, "p": net_profit_per * u})
        
        best_l1 = max(leg1_options, key=lambda x: x['p'], default=None)
        best_l2 = max(leg2_options, key=lambda x: x['p'], default=None)
        total = (best_l1['p'] if best_l1 else 0) + (best_l2['p'] if best_l2 else 0)
        
        if total > 0:
            all_potential_loops.append({"hub": r_name, "key": h_key, "l1": best_l1, "l2": best_l2, "total": total})

    all_potential_loops.sort(key=lambda x: x['total'], reverse=True)
    
    if not all_potential_loops:
        summary += "No profitable round-trips found for current market buy orders. Local manufacturing or hauling uncompressed might be better.\n\n"
    
    for i, r in enumerate(all_potential_loops[:3], 1):
        summary += f"### {i}. The {r['hub']} Round-Trip ({r['key']})\n"
        if r['l1']: summary += f"- **OUT:** {r['l1']['u']:,} x {r['l1']['name']} (Jita -> {r['key']}) -> Profit: **{r['l1']['p']/1e6:.2f}M**\n"
        else: summary += f"- **OUT:** No profitable Jita -> Hub arbitrage found.\n"
        if r['l2']: summary += f"- **IN:** {r['l2']['u']:,} x {r['l2']['name']} ({r['key']} -> Jita) -> Profit: **{r['l2']['p']/1e6:.2f}M**\n"
        else: summary += f"- **IN:** No profitable Hub -> Jita arbitrage found.\n"
        summary += f"**Predicted Round-Trip Profit: {r['total']/1e6:,.1f} Million ISK**\n\n"

    summary += "## ℹ️ Station Reference\n"
    for k, v in STATIONS.items(): summary += f"**{k}** ({v['region']}): {v['name']}\n\n"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Logic Finalized.")
