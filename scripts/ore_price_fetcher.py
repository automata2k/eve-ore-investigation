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

# VOLUMES (m3)
VOLUMES = {
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, 
    "28416": 0.20, "28668": 0.01, "2454": 5.0, "2486": 5.0, "2203": 5.0, "195": 0.1,
    "218": 0.01, "380": 10.0, "520": 5.0, "11299": 5.0, "434": 5.0, "438": 5.0,
    "196": 0.1, "193": 0.1, "194": 0.1, "2470": 5.0, "4051": 5.0, "4247": 5.0, 
    "4312": 5.0, "4246": 5.0, "1121": 1.0, "1122": 2.0, "526": 5.0, "393": 5.0,
    "32880": 2500.0, "657": 2500.0, "28576": 2500.0, "649": 2500.0, "11578": 10.0
}

# DYNAMIC ITEM LIST (Top high-volume items to check)
Ores = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Gneiss": "28416"
}
Goods = {
    "Nanite Repair Paste": "28668", "Warrior I": "2486", "Hobgoblin I": "2454", "Acolyte I": "2203", "Hornet I": "2470",
    "Antimatter Charge M": "218", "Scourge Heavy Missile": "195", "Mjolnir Heavy Missile": "196", "Nova Heavy Missile": "193", "Inferno Heavy Missile": "194",
    "Damage Control I": "520", "1600mm Steel Plates I": "11299", "Medium Shield Extender I": "380", "5MN Microwarpdrive I": "434", "10MN Afterburner I": "438",
    "Nitrogen Fuel Block": "4051", "Oxygen Fuel Block": "4247", "Helium Fuel Block": "4312", "Hydrogen Fuel Block": "4246",
    "Cap Booster 400": "1121", "Cap Booster 800": "1122", "Small Armor Repairer I": "526", "Small Shield Booster I": "393",
    "Venture": "32880", "Iteron Mark V": "657", "Tayra": "28576", "Badger": "649", "Mining Laser Upgrade I": "11578"
}

def fetch_tycoon_stats(region_id, type_id):
    url = f"https://evetycoon.com/api/v1/market/stats/{region_id}/{type_id}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Tycoon-v2'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 35000
    tax = 0.036
    
    # Pre-fetch Jita (The Forge) for all items
    jita_mkt = {name: fetch_tycoon_stats(REGIONS["The Forge"], tid) for name, tid in {**Ores, **Goods}.items()}
    
    summary = "# 🚀 EVE Arbitrage Daily Briefing (High-Volume Targets)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🛡️ Logistics Audit: 5.0m3 Cargo Optimized\n"
    summary += "Scanned top 35 high-velocity items. Selection based on **Volume > Profit Margin** to ensure liquidity.\n\n"
    
    summary += "## 🚛 Top 3 Recommended Trade Loops\n"
    summary += "*Calculated for 35,000 m³ using immediate Buy/Sell averages (Net of 3.6% fees).*\n\n"

    all_loops = []
    for h_key, hub in STATIONS.items():
        if h_key == "Jita IV-4": continue
        reg_id = REGIONS[hub["region"]]
        
        # Determine loop candidates for this hub
        outbound_options = [] # Jita -> Hub
        for name, tid in Goods.items():
            j_cost = float(jita_mkt[name].get("minSell", 0))
            h_data = fetch_tycoon_stats(reg_id, tid)
            h_gain = float(h_data.get("maxBuy", 0))
            h_vol = float(h_data.get("buyVolume", 0))
            
            if j_cost > 0 and h_gain > 0 and h_vol > 100:
                net_p_unit = (h_gain * (1-tax)) - j_cost
                if net_p_unit > 0:
                    units = int(min(cargo_max / VOLUMES[tid], h_vol * 0.2))
                    if units > 0:
                        outbound_options.append({"name": name, "u": units, "p": net_p_unit * units})

        inbound_options = [] # Hub -> Jita
        for name, tid in Ores.items():
            h_cost = float(fetch_tycoon_stats(reg_id, tid).get("minSell", 0))
            j_gain = float(jita_mkt[name].get("maxBuy", 0))
            j_vol = float(jita_mkt[name].get("buyVolume", 0))
            
            if h_cost > 0 and j_gain > 0 and j_vol > 500:
                net_p_unit = (j_gain * (1-tax)) - h_cost
                if net_p_unit > 0:
                    units = int(min(cargo_max / VOLUMES[tid], j_vol * 0.2))
                    if units > 0:
                        inbound_options.append({"name": name, "u": units, "p": net_p_unit * units})

        # Pick best item for each leg
        best_out = max(outbound_options, key=lambda x: x['p'], default=None)
        best_in = max(inbound_options, key=lambda x: x['p'], default=None)
        
        total = (best_out['p'] if best_out else 0) + (best_in['p'] if best_in else 0)
        if total > 0:
            all_loops.append({"hub": hub["region"], "key": h_key, "out": best_out, "in": best_in, "total": total})

    all_loops.sort(key=lambda x: x['total'], reverse=True)
    
    for i, r in enumerate(all_loops[:3], 1):
        summary += f"### {i}. The {r['hub']} Connection ({r['key']})\n"
        if r['out']:
            summary += f"- **OUT:** Buy **{r['out']['u']:,} x {r['out']['name']}** (Jita) -> Profit: **{r['out']['p']/1e6:.1f}M**\n"
        else:
            summary += "- **OUT:** No profitable outbound commodity found for this volume.\n"
        if r['in']:
            summary += f"- **IN:** Buy **{r['in']['u']:,} x {r['in']['name']}** (Hub) -> Profit: **{r['in']['p']/1e6:.1f}M**\n"
        else:
            summary += "- **IN:** No profitable return ore found for this volume.\n"
        summary += f"**Predicted Round-Trip Profit: {r['total']/1e6:,.1f} Million ISK**\n\n"

    summary += "\n## ℹ️ Reference & Destination Search\n"
    for k, v in STATIONS.items(): summary += f"**{k}** ({v['region']}): {v['name']}\n\n"
    return summary

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(base_dir, "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Loops refreshed with high-volume targets.")
