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

# ITEM VOLUMES (m3) - Used for Cargo Profit Calculations
# Values are per unit
VOLUMES = {
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15,  # Compressed Ores
    "28399": 0.12, "28394": 0.12, "28404": 0.20, "28407": 0.20,
    "28410": 0.20, "28416": 0.20, "28415": 0.20, "28418": 0.20,
    "195": 0.1, "196": 0.1, "193": 0.1, "194": 0.1,             # Heavy Missiles
    "28668": 0.01, "1121": 1.0,                               # Essentials
    "2454": 5.0, "2464": 5.0, "2203": 5.0, "2470": 5.0          # Drones
}

# ANTI-TRAP THRESHOLDS
VOLUME_THRESHOLDS = {
    "SHIPS": 3,
    "MODULES": 10,
    "AMMO": 5000,
    "DRONES": 50,
    "ESSENTIALS": 100
}

TARGET_TYPES = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394",
    "Compressed Jaspet": "28404", "Compressed Hemorphite": "28407", "Compressed Hedbergite": "28410",
    "Compressed Gneiss": "28416", "Compressed Dark Ochre": "28415", "Compressed Crokite": "28418"
}

MINERAL_TYPES = {
    "Tritanium": "34", "Pyerite": "35", "Mexallon": "36", "Isogen": "37",
    "Nocxium": "38", "Zydrine": "39", "Megacyber": "40", "Morphite": "11399"
}

MFG_SHIPS = {
    "Venture": "32880", "Iteron Mark V": "657", "Badger": "649", "Tayra": "28576"
}

MFG_MODULES = {
    "1MN Afterburner I": "436", "10MN Afterburner I": "438", "5MN Microwarpdrive I": "434",
    "Stasis Webifier I": "444", "Warp Scrambler I": "447", "Warp Disruptor I": "440",
    "Damage Control I": "520", "Multispectrum Shield Hardener I": "2281", "Cap Recharger I": "1192",
    "Drone Damage Amplifier I": "23559", "Medium Shield Extender I": "380", "1600mm Steel Plates I": "11299"
}

MFG_AMMO = {
    "Antimatter Charge S": "230", "Antimatter Charge M": "218", "Antimatter Charge L": "206",
    "Scourge Heavy Missile": "195", "Scourge Light Missile": "191", "EMP S": "183", "EMP M": "177",
    "Hobgoblin I": "2454", "Warrior I": "2464", "Acolyte I": "2203"
}

MISSION_ESSENTIALS = {
    "Scourge Heavy Missile": "195", "Mjolnir Heavy Missile": "196", "Nova Heavy Missile": "193",
    "Nanite Repair Paste": "28668", "Cap Booster 400": "1121", "Hobgoblin I": "2454",
    "Warrior I": "2464", "Acolyte I": "2203"
}

MFG_ESSENTIALS = {
    "Nanite Repair Paste": "28668", "Cap Booster 400": "1121", "Cap Booster 800": "1122",
    "Mining Laser I": "483", "Mining Laser Upgrade I": "11578", "Warp Core Stabilizer I": "524",
    "Mobile Tractor Unit": "33477", "Mobile Depot": "33474", "Oxygen Fuel Block": "4247",
    "Nitrogen Fuel Block": "4051", "Hydrogen Fuel Block": "4246", "Helium Fuel Block": "4312"
}

def get_threshold(name, tid):
    if tid in MFG_SHIPS.values(): return VOLUME_THRESHOLDS["SHIPS"]
    if tid in MFG_MODULES.values(): return VOLUME_THRESHOLDS["MODULES"]
    if "Missile" in name or "Charge" in name or "EMP" in name: return VOLUME_THRESHOLDS["AMMO"]
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
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {}

def format_vol(vol):
    if vol >= 1e9: return f"{vol/1e9:.1f}B"
    if vol >= 1e6: return f"{vol/1e6:.1f}M"
    if vol >= 1e3: return f"{vol/1e3:.1f}k"
    return str(int(vol))

def calculate_spreads():
    cargo_max = 50000
    all_needed_ids = list(TARGET_TYPES.values()) + list(MINERAL_TYPES.values()) + \
                     list(MFG_SHIPS.values()) + list(MFG_MODULES.values()) + \
                     list(MFG_AMMO.values()) + list(MFG_ESSENTIALS.values()) + \
                     list(MISSION_ESSENTIALS.values())
    
    jita = fetch_prices(STATIONS["Jita IV-4"]["id"], all_needed_ids)
    
    # Fetch all data for all hubs for route planning
    hub_ids = ["Amarr VIII", "Dodixie IX", "Osmon II", "Apanake IV", "Lanngisi VII"]
    station_data = {}
    for h in hub_ids:
        station_data[h] = fetch_prices(STATIONS[h]["id"], list(TARGET_TYPES.values()) + list(MISSION_ESSENTIALS.values()))

    # --- REPORT GENERATION ---
    summary = "# 🚀 EVE Arbitrage Weekly Briefing\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

    # --- TOP TRADE RUNS ---
    summary += "## 🚛 Daily Trade Run (50,000 m³ Recommendation)\n"
    
    routes = []
    for h_key in hub_ids:
        # 1. Best Outbound (Jita -> Hub)
        best_out = None
        best_out_profit = 0
        for name, tid in MISSION_ESSENTIALS.items():
            if tid not in VOLUMES: continue
            j_buy = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
            h_sell = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0))
            h_vol = float(station_data[h_key].get(tid, {}).get("sell", {}).get("volume", 0))
            if j_buy > 0 and h_sell > 0 and h_vol > 10:
                markup = ((h_sell - j_buy) / j_buy) * 100
                if markup > 5.0 and markup < 500:
                    units = cargo_max / VOLUMES[tid]
                    profit = (h_sell - j_buy) * units
                    if profit > best_out_profit:
                        best_out_profit = profit
                        best_out = {"name": name, "profit": profit, "units": int(units)}

        # 2. Best Inbound (Hub -> Jita) - Focused on Ores
        best_in = None
        best_in_profit = 0
        for name, tid in TARGET_TYPES.items():
            if tid not in VOLUMES: continue
            h_buy = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0)) # Buying from hub market
            j_sell = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
            if h_buy > 0 and j_sell > 0:
                spread = ((j_sell - h_buy) / h_buy) * 100
                if spread > 2.0:
                    units = cargo_max / VOLUMES[tid]
                    profit = (j_sell - h_buy) * units
                    if profit > best_in_profit:
                        best_in_profit = profit
                        best_in = {"name": name, "profit": profit, "units": int(units)}

        total = best_out_profit + best_in_profit
        if total > 1000000: # Only bother with routes making > 1M ISK
            routes.append({"hub": h_key, "out": best_out, "in": best_in, "total": total})

    routes.sort(key=lambda x: x['total'], reverse=True)
    
    for i, r in enumerate(routes[:2], 1): # Show Top 2 best routes
        summary += f"### Run {i}: The {STATIONS[r['hub']]['region']} Loop\n"
        summary += f"1. **OUTBOUND:** Buy **{r['out']['units']:,} x {r['out']['name']}** in Jita. \n"
        summary += f"   - Sell at **{r['hub']}** for ~{r['out']['profit']/1e6:.1f}M ISK profit.\n"
        if r['in']:
            summary += f"2. **INBOUND:** Buy **{r['in']['units']:,} x {r['in']['name']}** at {r['hub']}. \n"
            summary += f"   - Sell in **Jita** for ~{r['in']['profit']/1e6:.1f}M ISK profit.\n"
        else:
            summary += "2. **INBOUND:** No profitable ore spread found for return trip. Haul empty or check local missions.\n"
        summary += f"**ESTIMATED TOTAL PROFIT:** **{r['total']/1e6:,.1f} Million ISK**\n\n"

    # --- VERDICT ---
    summary += "## 🍤 Shrimp's Weekly Verdict\n"
    # (Existing Verdict Logic...)
    best_ore_spread = 0
    best_ore_name = ""
    for tid, name in {v: k for k, v in TARGET_TYPES.items()}.items():
        jita_p = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        for h_key in ["Amarr VIII", "Dodixie IX"]:
            p = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0))
            if jita_p > 0 and p > 0:
                spread = ((jita_p - p) / p) * 100
                if spread > best_ore_spread:
                    best_ore_spread = spread
                    best_ore_name = name

    mfg_candidates = []
    for d in [MFG_SHIPS, MFG_MODULES, MFG_AMMO, MFG_ESSENTIALS]:
        for name, tid in d.items():
            info = jita.get(tid, {})
            s = float(info.get("sell", {}).get("min", 0))
            b = float(info.get("buy", {}).get("max", 0))
            v = float(info.get("sell", {}).get("volume", 0))
            if s > 0 and b > 0:
                spread = ((s - b) / b) * 100
                thresh = get_threshold(name, tid)
                if v >= thresh:
                    mfg_candidates.append({"name": name, "spread": spread, "vol": v})

    mfg_candidates.sort(key=lambda x: x['spread'], reverse=True)
    top_5 = mfg_candidates[:5]

    if top_5 and top_5[0]['spread'] > best_ore_spread + 5:
        summary += f"**Verdict: MANUFACTURE.** Verified liquidity-adjusted spreads outperform ore hauling.\n\n"
        summary += "### 💎 Jita Top 5 Manufacturing Items:\n"
        for i, item in enumerate(top_5, 1):
            summary += f"{i}. **{item['name']}** ({item['spread']:.1f}% spread, {format_vol(item['vol'])} volume)\n"
        summary += "\n"
    else:
        summary += f"**Verdict: HAUL ORE.** Raw ore spreads (like **{best_ore_name}** at {best_ore_spread:.1f}%) are the safest play.\n\n"

    # --- TABLES ---
    summary += "## 🎯 Mission Hub Arbitrage (Buy Jita -> Scale Hub)\n"
    summary += "| Destination Hub | Item | Hub Price | Jita Buy | Markup | Hub Stock |\n"
    summary += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for h_key in ["Osmon II", "Apanake IV", "Lanngisi VII"]:
        data = station_data[h_key]
        for name, tid in MISSION_ESSENTIALS.items():
            j_buy = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
            h_sell = float(data.get(tid, {}).get("sell", {}).get("min", 0))
            h_vol = float(data.get(tid, {}).get("sell", {}).get("volume", 0))
            if j_buy > 0 and h_sell > 0:
                markup = ((h_sell - j_buy) / j_buy) * 100
                thresh = get_threshold(name, tid)
                if 5.0 <= markup <= 500.0 and h_vol >= (thresh / 10): 
                    summary += f"| {h_key} | {name} | {h_sell:,.2f} | {j_buy:,.2f} | **{markup:.1f}%** | {int(h_vol)} |\n"

    summary += "\n## 📈 High Sec Ore Spreads\n"
    summary += "| Ore Type | Origin Hub | Local Price | Jita Spread % |\n| :--- | :--- | :--- | :--- |\n"
    for name, tid in sorted(TARGET_TYPES.items()):
        jita_p = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        for h_key in ["Amarr VIII", "Dodixie IX"]:
            p = float(station_data[h_key].get(tid, {}).get("sell", {}).get("min", 0))
            if jita_p > 0 and p > 0:
                spread = ((jita_p - p) / p) * 100
                s_txt = f"**{spread:.1f}%**" if spread >= 10.0 else f"{spread:.1f}%"
                summary += f"| {name} | {h_key} | {p:,.2f} | {s_txt} |\n"

    summary += "\n## 💎 Jita Mineral Index\n"
    summary += "| Mineral | Jita Sell | Jita Buy | 24h Vol |\n| :--- | :--- | :--- | :--- |\n"
    for name, tid in sorted(MINERAL_TYPES.items()):
        info = jita.get(tid, {})
        s = float(info.get("sell", {}).get("min", 0))
        b = float(info.get("buy", {}).get("max", 0))
        v = float(info.get("sell", {}).get("volume", 0))
        summary += f"| {name} | {s:,.2f} | {b:,.2f} | {format_vol(v)} |\n"

    summary += "\n## ℹ️ Station Reference Guide\n"
    summary += "| Hub Key | Region | Full Station Name (Set Destination Here) |\n| :--- | :--- | :--- |\n"
    for k, v in STATIONS.items():
        summary += f"| **{k}** | {v['region']} | {v['name']} |\n"

    summary += "\n\n--- \n*Generated by the Shrimp Market Bot. Includes belt ores and anomaly/escalation types.* 🍤"
    return summary

if __name__ == "__main__":
    report = calculate_spreads()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(repo_root, "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(report)
    print(f"Analysis complete. Full report synced to {report_path}")
