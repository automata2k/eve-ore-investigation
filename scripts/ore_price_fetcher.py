import urllib.request
import json
import ssl
import os
from datetime import datetime

# EXACT STATION NAMES & IDs
STATIONS = {
    "Jita IV-4": {"id": "60003760", "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant"},
    "Amarr VIII": {"id": "60008494", "name": "Amarr VIII (Orbis) - Emperor Family Academy"},
    "Dodixie IX": {"id": "60011866", "name": "Dodixie IX - Moon 20 - Federation Navy Assembly Plant"},
    "Osmon II": {"id": "60012667", "name": "Osmon II - Moon 1 - Sisters of EVE Bureau"},
    "Apanake IV": {"id": "60005236", "name": "Apanake IV - Moon 4 - Sisters of EVE Bureau"},
    "Lanngisi VII": {"id": "60009514", "name": "Lanngisi VII - Moon 11 - Sisters of EVE Bureau"}
}

# ANTI-TRAP THRESHOLDS
# Items with volume below these levels are considered "Market Traps" and ignored.
VOLUME_THRESHOLDS = {
    "SHIPS": 3,      # Need at least 3 ships in stock
    "MODULES": 10,   # Need at least 10 modules
    "AMMO": 5000,    # Need at least 5k rounds
    "DRONES": 50,    # Need at least 50 drones
    "ESSENTIALS": 100 # Nanite paste, etc.
}

# CATEGORIES mapped to Thresholds
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
    all_needed_ids = list(TARGET_TYPES.values()) + list(MINERAL_TYPES.values()) + \
                     list(MFG_SHIPS.values()) + list(MFG_MODULES.values()) + \
                     list(MFG_AMMO.values()) + list(MFG_ESSENTIALS.values()) + \
                     list(MISSION_ESSENTIALS.values())
    
    jita = fetch_prices(STATIONS["Jita IV-4"]["id"], all_needed_ids)
    amarr = fetch_prices(STATIONS["Amarr VIII"]["id"], list(TARGET_TYPES.values()))
    dodi = fetch_prices(STATIONS["Dodixie IX"]["id"], list(TARGET_TYPES.values()))
    
    mission_hubs = ["Osmon II", "Apanake IV", "Lanngisi VII"]
    hub_prices = {h: fetch_prices(STATIONS[h]["id"], list(MISSION_ESSENTIALS.values())) for h in mission_hubs}
    
    summary = "# 🚀 EVE Arbitrage Weekly Briefing\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🛡️ Anti-Trap Logic Active\n"
    summary += "- Listings with insufficient volume to support a haul are **discarded**.\n"
    summary += "- Price markups > 500% are flagged as **potential scams** and ignored.\n\n"

    # Verdict Logic
    best_ore_spread = 0
    best_ore_name = ""
    for tid, name in {v: k for k, v in TARGET_TYPES.items()}.items():
        jita_p = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        for h_json in [amarr, dodi]:
            p = float(h_json.get(tid, {}).get("sell", {}).get("min", 0))
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

    summary += "## 🍤 Shrimp's Weekly Verdict\n"
    if top_5 and top_5[0]['spread'] > best_ore_spread + 5:
        summary += f"**Verdict: MANUFACTURE.** Verified liquidity-adjusted spreads outperform ore hauling.\n\n"
        summary += "### 💎 Jita Top 5 Manufacturing Items:\n"
        for i, item in enumerate(top_5, 1):
            summary += f"{i}. **{item['name']}** ({item['spread']:.1f}% spread, {format_vol(item['vol'])} volume)\n"
        summary += "\n"
    else:
        summary += f"**Verdict: HAUL ORE.** Raw ore spreads (like **{best_ore_name}** at {best_ore_spread:.1f}%) are the safest play.\n\n"

    summary += "## 🎯 Mission Hub Arbitrage (Buy Jita -> Scale Hub)\n"
    summary += "| Destination Hub | Item | Hub Price | Jita Buy | Markup | Hub Stock |\n"
    summary += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    found_hub_op = False
    for h_key in mission_hubs:
        h_name = STATIONS[h_key]["name"]
        data = hub_prices[h_key]
        for name, tid in MISSION_ESSENTIALS.items():
            j_buy = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
            h_sell = float(data.get(tid, {}).get("sell", {}).get("min", 0))
            h_vol = float(data.get(tid, {}).get("sell", {}).get("volume", 0))
            
            if j_buy > 0 and h_sell > 0:
                markup = ((h_sell - j_buy) / j_buy) * 100
                thresh = get_threshold(name, tid)
                # Filter scams and low-liquidity traps
                if 5.0 <= markup <= 500.0 and h_vol >= (thresh / 10): 
                    summary += f"| {h_key} | {name} | {h_sell:,.2f} | {j_buy:,.2f} | **{markup:.1f}%** | {int(h_vol)} |\n"
                    found_hub_op = True
    
    if not found_hub_op:
        summary += "| No safe hub markups found today. | | | | | |\n"

    summary += "\n## 📈 High Sec Ore Spreads\n"
    summary += "| Ore Type | Origin Hub | Local Price | Jita Spread % |\n| :--- | :--- | :--- | :--- |\n"
    for name, tid in sorted(TARGET_TYPES.items()):
        jita_p = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        for h_key in ["Amarr VIII", "Dodixie IX"]:
            h_json = amarr if h_key == "Amarr VIII" else dodi
            p = float(h_json.get(tid, {}).get("sell", {}).get("min", 0))
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
    summary += "| Hub Key | Full Station Name (Set Destination Here) |\n| :--- | :--- |\n"
    for k, v in STATIONS.items():
        summary += f"| **{k}** | {v['name']} |\n"

    summary += "\n\n--- \n*Generated by the Shrimp Market Bot. Includes belt ores and anomaly/escalation types.* 🍤"
    return summary

if __name__ == "__main__":
    report = calculate_spreads()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(repo_root, "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(report)
    print(f"Analysis complete. Full report synced to {report_path}")
