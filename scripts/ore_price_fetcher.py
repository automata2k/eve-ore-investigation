import urllib.request
import json
import ssl
import os
from datetime import datetime

# EXACT STATION NAMES, REGIONS & IDs
STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant", "region": "The Forge"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy", "region": "Domain"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant", "region": "Sinq Laison"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau", "region": "The Forge"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau", "region": "Genesis"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau", "region": "Metropolis"}
}

# CORRECTED ITEM IDs & VOLUMES (m3)
VOLUMES = {
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15,  # Compressed Ores
    "28399": 0.12, "28394": 0.12, "28404": 0.20, "28416": 0.20,
    "195": 0.1, "196": 0.1, "193": 0.1, "194": 0.1,             # Heavy Missiles
    "28668": 0.01, "1121": 1.0,                               # Essentials
    "2454": 5.0, "2486": 5.0, "2203": 5.0, "2470": 5.0,         # Drones (Warrior I fixed to 2486)
    "218": 0.01                                               # Antimatter M
}

TARGET_TYPES = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394",
    "Compressed Gneiss": "28416"
}

MFG_SHIPS = {"Venture": "32880", "Iteron Mark V": "657", "Badger": "649", "Tayra": "28576"}
MFG_AMMO = {"Antimatter Charge M": "218", "Scourge Heavy Missile": "195", "Hobgoblin I": "2454", "Warrior I": "2486"}
MISSION_ESSENTIALS = {"Scourge Heavy Missile": "195", "Nova Heavy Missile": "193", "Nanite Repair Paste": "28668", "Warrior I": "2486"}

def fetch_prices(station_id, type_ids):
    ids_str = ",".join(set(type_ids))
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={station_id}&types={ids_str}"
    req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-Shrimp-Bot/1.0'})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode())
    except: return {}

def format_vol(vol):
    if vol >= 1e9: return f"{vol/1e9:.1f}B"
    if vol >= 1e6: return f"{vol/1e6:.1f}M"
    if vol >= 1e3: return f"{vol/1e3:.1f}k"
    return str(int(vol))

def calculate_spreads():
    cargo_max = 50000
    fee_estimate = 0.05 # Conservative 5% broker/sales tax
    
    all_needed_ids = list(TARGET_TYPES.values()) + list(MFG_SHIPS.values()) + \
                     list(MFG_AMMO.values()) + list(MISSION_ESSENTIALS.values())
    
    jita = fetch_prices(STATIONS["Jita IV-4"]["id"], all_needed_ids)
    hub_ids = ["Amarr VIII", "Dodixie IX", "Osmon II", "Apanake IV", "Lanngisi VII"]
    station_data = {h: fetch_prices(STATIONS[h]["id"], all_needed_ids) for h in hub_ids}

    # --- TRADE LOOP ANALYZER ---
    summary = "# 🚀 EVE Arbitrage Weekly Briefing\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "## 🚛 Daily Trade Run (Optimized 50,000 m³)\n"
    summary += "Calculated using **Payload Logic**: Immediate buy at source vs immediate sell at dest, minus 5% fees.\n\n"
    
    potential_runs = []
    for h_key in hub_ids:
        h_info = STATIONS[h_key]
        h_prices = station_data[h_key]
        
        # outbound: Jita -> Hub
        best_out = None
        best_out_p = -1e12
        for name, tid in MISSION_ESSENTIALS.items():
            if tid not in VOLUMES: continue
            j_buy_cost = float(jita.get(tid, {}).get("sell", {}).get("min", 0)) # Buying from Jita Sell orders
            h_sell_price = float(h_prices.get(tid, {}).get("buy", {}).get("max", 0)) # Dumping into Hub Buy orders
            h_vol = float(h_prices.get(tid, {}).get("buy", {}).get("volume", 0)) # Buy order depth
            
            if j_buy_cost > 0 and h_sell_price > 0:
                net_profit_per = (h_sell_price * (1 - fee_estimate)) - j_buy_cost
                if net_profit_per > 0:
                    u = min(cargo_max / VOLUMES[tid], h_vol)
                    p = net_profit_per * u
                    if p > best_out_p:
                        best_out_p = p
                        best_out = {"name": name, "units": int(u), "profit": p, "cost": j_buy_cost * u}

        # inbound: Hub -> Jita
        best_in = None
        best_in_p = -1e12
        for name, tid in TARGET_TYPES.items():
            if tid not in VOLUMES: continue
            h_buy_cost = float(h_prices.get(tid, {}).get("sell", {}).get("min", 0)) # Buying from Hub Sell orders
            j_sell_price = float(jita.get(tid, {}).get("buy", {}).get("max", 0)) # Dumping into Jita Buy orders
            j_vol = float(jita.get(tid, {}).get("buy", {}).get("volume", 0))
            
            if h_buy_cost > 0 and j_sell_price > 0:
                net_profit_per = (j_sell_price * (1 - fee_estimate)) - h_buy_cost
                if net_profit_per > 0:
                    u = min(cargo_max / VOLUMES[tid], j_vol)
                    p = net_profit_per * u
                    if p > best_in_p:
                        best_in_p = p
                        best_in = {"name": name, "units": int(u), "profit": p}
        
        total_p = (best_out_p if best_out_p > 0 else 0) + (best_in_p if best_in_p > 0 else 0)
        if total_p > 0:
            potential_runs.append({"hub": h_key, "out": best_out, "in": best_in, "total": total_p})

    potential_runs.sort(key=lambda x: x['total'], reverse=True)
    for i, r in enumerate(potential_runs[:3], 1):
        summary += f"### {i}. The {STATIONS[r['hub']]['region']} High-Sec Loop\n"
        if r['out'] and r['out']['profit'] > 0:
            summary += f"- **Outbound (Jita -> {r['hub']}):** Buy **{r['out']['units']:,} x {r['out']['name']}**. (Investment: {r['out']['cost']/1e6:.1f}M, Profit: **{r['out']['profit']/1e6:.1f}M**)\n"
        else: summary += f"- **Outbound (Jita -> {r['hub']}):** No immediate arbitrage found.\n"
        if r['in'] and r['in']['profit'] > 0:
            summary += f"- **Inbound ({r['hub']} -> Jita):** Buy **{r['in']['units']:,} x {r['in']['name']}**. (Profit: **{r['in']['profit']/1e6:.1f}M**)\n"
        else: summary += f"- **Inbound ({r['hub']} -> Jita):** No immediate arbitrage found.\n"
        summary += f"**TOTAL ROUND-TRIP PROFIT: {r['total']/1e6:.1f} Million ISK**\n\n"

    # --- STANDY TABLES ---
    summary += "## 📈 High Sec Ore Spreads (Immediate Selling Profit)\n"
    summary += "| Ore Type | Origin Hub | Jita Buy (Net) | Local Sell | Markup |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for name, tid in sorted(TARGET_TYPES.items()):
        j_buy_order = float(jita.get(tid, {}).get("buy", {}).get("max", 0)) * (1 - fee_estimate)
        for h_key in ["Amarr VIII", "Dodixie IX"]:
            h_sell_price = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0))
            if j_buy_order > 0 and h_sell_price > 0:
                spread = ((j_buy_order - h_sell_price) / h_sell_price) * 100
                if spread > 0:
                    summary += f"| {name} | {h_key} | {j_buy_order:,.2f} | {h_sell_price:,.2f} | **{spread:.1f}%** |\n"

    summary += "\n## 🛰️ Jita Demand (Immediate Arbitrage)\n"
    summary += "| Item | Jita Buy (Net) | Jita Sell (Cost) | Spread |\n| :--- | :--- | :--- | :--- |\n"
    for d in [MFG_SHIPS, MFG_AMMO]:
        for name, tid in d.items():
            s = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
            b = float(jita.get(tid, {}).get("buy", {}).get("max", 0)) * (1 - fee_estimate)
            if s > 0 and b > 0:
                summary += f"| {name} | {b:,.2f} | {s:,.2f} | {((b-s)/s)*100:.1f}% |\n"

    summary += "\n## ℹ️ Station Reference Guide\n| Hub Key | Region | Full Station Name |\n| :--- | :--- | :--- |\n"
    for k, v in STATIONS.items(): summary += f"| **{k}** | {v['region']} | {v['name']} |\n"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market logic fixed and updated.")
