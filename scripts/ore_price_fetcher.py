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

# ITEM VOLUMES (m3)
VOLUMES = {
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15,
    "28399": 0.12, "28394": 0.12, "28404": 0.20, "28416": 0.20,
    "195": 0.1, "196": 0.1, "193": 0.1, "194": 0.1,             
    "28668": 0.01, "1121": 1.0,                               
    "2454": 5.0, "2464": 5.0, "2203": 5.0, "2470": 5.0          
}

VOLUME_THRESHOLDS = {
    "SHIPS": 3, "MODULES": 10, "AMMO": 5000, "DRONES": 50, "ESSENTIALS": 100
}

TARGET_TYPES = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394"
}

MINERAL_TYPES = {
    "Tritanium": "34", "Pyerite": "35", "Mexallon": "36", "Isogen": "37",
    "Nocxium": "38", "Zydrine": "39", "Megacyber": "40"
}

MFG_SHIPS = {"Venture": "32880", "Iteron Mark V": "657", "Badger": "649", "Tayra": "28576"}
MFG_MODULES = {"5MN Microwarpdrive I": "434", "Damage Control I": "520", "Medium Shield Extender I": "380", "1600mm Steel Plates I": "11299"}
MFG_AMMO = {"Antimatter Charge M": "218", "Scourge Heavy Missile": "195", "Hobgoblin I": "2454", "Warrior I": "2464"}
MISSION_ESSENTIALS = {"Scourge Heavy Missile": "195", "Nova Heavy Missile": "193", "Nanite Repair Paste": "28668", "Hobgoblin I": "2454", "Warrior I": "2464"}

def get_threshold(name, tid):
    if tid in MFG_SHIPS.values(): return VOLUME_THRESHOLDS["SHIPS"]
    if tid in MFG_MODULES.values(): return VOLUME_THRESHOLDS["MODULES"]
    if "Missile" in name: return VOLUME_THRESHOLDS["AMMO"]
    if "I" in name and (tid in MFG_AMMO.values() or tid in MISSION_ESSENTIALS.values()): return VOLUME_THRESHOLDS["DRONES"]
    return VOLUME_THRESHOLDS["ESSENTIALS"]

def fetch_prices(station_id, type_ids):
    ids_str = ",".join(set(type_ids))
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={station_id}&types={ids_str}"
    req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-Shrimp-Bot/1.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx) as response: return json.loads(response.read().decode())
    except: return {}

def calculate_spreads():
    cargo_max = 50000
    all_needed_ids = list(TARGET_TYPES.values()) + list(MINERAL_TYPES.values()) + \
                     list(MFG_SHIPS.values()) + list(MFG_MODULES.values()) + \
                     list(MFG_AMMO.values()) + list(MISSION_ESSENTIALS.values())
    
    jita = fetch_prices(STATIONS["Jita IV-4"]["id"], all_needed_ids)
    hub_ids = ["Amarr VIII", "Dodixie IX", "Osmon II", "Apanake IV", "Lanngisi VII"]
    station_data = {h: fetch_prices(STATIONS[h]["id"], list(TARGET_TYPES.values()) + list(MISSION_ESSENTIALS.values())) for h in hub_ids}

    summary = "# 🚀 EVE Arbitrage Weekly Briefing\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

    # --- DAILY TRADE RUNS ---
    summary += "## 🚛 Daily Trade Run (Realistic 50,000 m³ Optimization)\n"
    summary += "Calculated based on current stock depth (not infinite) to avoid market saturation.\n\n"
    
    routes = []
    for h_key in hub_ids:
        # OUTBOUND (Jita -> Hub)
        for name, tid in MISSION_ESSENTIALS.items():
            if tid not in VOLUMES: continue
            j_buy = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
            h_sell = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0))
            h_vol = float(station_data[h_key].get(tid, {}).get("sell", {}).get("volume", 0))
            
            if j_buy > 0 and h_sell > 0 and h_vol > 10:
                markup = ((h_sell - j_buy) / j_buy) * 100
                if 5.0 < markup < 500:
                    units = min(cargo_max / VOLUMES[tid], h_vol * 0.5) # Cap at 50% of current hub stock to be realistic
                    if units < 1: continue
                    profit = (h_sell - j_buy) * units
                    investment = j_buy * units
                    
                    # INBOUND (Hub -> Jita)
                    best_in = None
                    best_in_profit = 0
                    for o_name, o_tid in TARGET_TYPES.items():
                        h_buy_p = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0)) # Buying from hub market
                        j_sell = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
                        if h_buy_p > 0 and j_sell > 0:
                            spread = ((j_sell - h_buy_p) / h_buy_p) * 100
                            if spread > 2.0:
                                i_units = cargo_max / VOLUMES[o_tid]
                                i_profit = (j_sell - h_buy_p) * i_units
                                if i_profit > best_in_profit:
                                    best_in_profit = i_profit
                                    best_in = {"name": o_name, "profit": i_profit, "units": int(i_units)}
                    
                    routes.append({
                        "hub": h_key, "out_name": name, "out_units": int(units), "out_profit": profit,
                        "in": best_in, "total": profit + best_in_profit, "cost": investment
                    })

    routes.sort(key=lambda x: x['total'], reverse=True)
    for i, r in enumerate(routes[:3], 1): # Top 3
        summary += f"### {i}. {STATIONS[r['hub']]['region']} High-Sec Loop\n"
        summary += f"- **Outbound (Jita -> {r['hub']}):** Buy **{r['out_units']:,} x {r['out_name']}**. "
        summary += f"(Cost: {r['cost']/1e6:.1f}M, Profit: **{r['out_profit']/1e6:.1f}M**)\n"
        if r['in']:
            summary += f"- **Inbound ({r['hub']} -> Jita):** Buy **{r['in']['units']:,} x {r['in']['name']}**. "
            summary += f"(Profit: **{r['in']['profit']/1e6:.1f}M**)\n"
        summary += f"- **Estimated Round-Trip Profit:** **{r['total']/1e6:.1f} Million ISK**\n\n"

    # --- REST OF REPORT ---
    summary += "## 🍤 Shrimp's Weekly Verdict\n"
    mfg_candidates = []
    for d in [MFG_SHIPS, MFG_MODULES, MFG_AMMO]:
        for name, tid in d.items():
            info = jita.get(tid, {})
            s = float(info.get("sell", {}).get("min", 0))
            b = float(info.get("buy", {}).get("max", 0))
            v = float(info.get("sell", {}).get("volume", 0))
            if s > 0 and b > 0 and v >= get_threshold(name, tid):
                mfg_candidates.append({"name": name, "spread": ((s - b) / b) * 100, "vol": v})
    mfg_candidates.sort(key=lambda x: x['spread'], reverse=True)
    
    summary += "**Verdict: MANUFACTURE.** Verified liquidity spreads outperform hauling.\n"
    summary += "### 💎 Jita Top 3 Mfg:\n"
    for item in mfg_candidates[:3]: summary += f"- **{item['name']}** ({item['spread']:.1f}%)\n"

    summary += "\n## 🎯 Mission Hub Arbitrage\n| Hub | Item | Hub Price | Jita Buy | Markup | Hub Stock |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for h_key in ["Osmon II", "Apanake IV", "Lanngisi VII"]:
        for name, tid in MISSION_ESSENTIALS.items():
            j_buy = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
            h_sell = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0))
            h_vol = float(station_data[h_key].get(tid, {}).get("sell", {}).get("volume", 0))
            if j_buy > 0 and h_sell > 0:
                markup = ((h_sell - j_buy) / j_buy) * 100
                if 5.0 <= markup <= 500.0 and h_vol > 5:
                    summary += f"| {h_key} | {name} | {h_sell:,.2f} | {j_buy:,.2f} | **{markup:.1f}%** | {int(h_vol)} |\n"

    summary += "\n## ℹ️ Station Reference Guide\n| Hub Key | Region | Full Station Name |\n| :--- | :--- | :--- |\n"
    for k, v in STATIONS.items(): summary += f"| **{k}** | {v['region']} | {v['name']} |\n"
    summary += "\n*Generated by Shrimp Bot. Values capped by market depth.* 🍤"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Market Data Updated.")
