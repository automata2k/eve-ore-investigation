import urllib.request
import json
import ssl
import os
from datetime import datetime

# EVE Hub Station/Structure IDs
JITA_IV_4 = "60003760"
AMARR_VIII = "60008494"
DODIXIE_IX = "60011866"

# MISSION HUBS
HUBS = {
    "Osmon": "60004516",      # SoE Bureau (Guristas)
    "Apanake": "60005236",    # SoE Bureau (Sansha/Blood)
    "Lanngisi": "60009514"    # SoE Bureau (Angels)
}

# CATEGORIES
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

# General Demand Items
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
    "Scourge Heavy Missile": "195",
    "Mjolnir Heavy Missile": "196",
    "Inferno Heavy Missile": "194",
    "Nova Heavy Missile": "193",
    "Nanite Repair Paste": "28668",
    "Cap Booster 400": "1121",
    "Hobgoblin I": "2454",
    "Warrior I": "2464",
    "Acolyte I": "2203",
    "Hornet I": "2470"
}

MFG_ESSENTIALS = {
    "Nanite Repair Paste": "28668", "Cap Booster 400": "1121", "Cap Booster 800": "1122",
    "Mining Laser I": "483", "Mining Laser Upgrade I": "11578", "Warp Core Stabilizer I": "524",
    "Mobile Tractor Unit": "33477", "Mobile Depot": "33474", "Oxygen Fuel Block": "4247",
    "Nitrogen Fuel Block": "4051", "Hydrogen Fuel Block": "4246", "Helium Fuel Block": "4312"
}

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
        print(f"Error fetching data for station {station_id}: {e}")
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
    
    jita = fetch_prices(JITA_IV_4, all_needed_ids)
    amarr = fetch_prices(AMARR_VIII, list(TARGET_TYPES.values()))
    dodi = fetch_prices(DODIXIE_IX, list(TARGET_TYPES.values()))
    
    hub_data = {}
    for hub_name, hub_id in HUBS.items():
        hub_data[hub_name] = fetch_prices(hub_id, list(MISSION_ESSENTIALS.values()))
    
    summary = "# 🚀 EVE Arbitrage Weekly Briefing\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "Tracks compressed ore spreads, hub demand, and missioner essentials.\n\n"

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
                min_vol = 5 if tid in MFG_SHIPS.values() else 1000
                if v >= min_vol:
                    mfg_candidates.append({"name": name, "spread": spread, "vol": v})

    mfg_candidates.sort(key=lambda x: x['spread'], reverse=True)
    top_5 = mfg_candidates[:5]

    summary += "## 🍤 Shrimp's Weekly Verdict\n"
    if top_5 and top_5[0]['spread'] > best_ore_spread + 5:
        summary += f"**Verdict: MANUFACTURE.** Current manufacturing margins on high-liquidity items outperform raw hauling.\n\n"
        summary += "### 💎 Jita Top 5 Manufacturing Items:\n"
        for i, item in enumerate(top_5, 1):
            summary += f"{i}. **{item['name']}** ({item['spread']:.1f}% spread, {format_vol(item['vol'])} daily vol)\n"
        summary += "\n"
    else:
        summary += f"**Verdict: HAUL ORE.** Raw ore spreads (like **{best_ore_name}** at {best_ore_spread:.1f}%) are strong and carry less complexity.\n\n"

    summary += "## 📈 High Sec Market Spreads (Regional Hubs -> Jita)\n"
    summary += "| Ore Type | Hub | Local Price | Jita Spread % |\n| :--- | :--- | :--- | :--- |\n"
    for name, tid in sorted(TARGET_TYPES.items()):
        jita_p = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        for h_name, h_json in [("Amarr", amarr), ("Dodixie", dodi)]:
            p = float(h_json.get(tid, {}).get("sell", {}).get("min", 0))
            if jita_p > 0 and p > 0:
                spread = ((jita_p - p) / p) * 100
                s_txt = f"**{spread:.1f}%**" if spread >= 10.0 else f"{spread:.1f}%"
                summary += f"| {name} | {h_name} | {p:,.2f} | {s_txt} |\n"

    summary += "\n## 💎 Jita Mineral Index (Raw Demand)\n"
    summary += "| Mineral | Jita Sell | Jita Buy | 24h Vol |\n| :--- | :--- | :--- | :--- |\n"
    for name, tid in sorted(MINERAL_TYPES.items()):
        info = jita.get(tid, {})
        s = float(info.get("sell", {}).get("min", 0))
        b = float(info.get("buy", {}).get("max", 0))
        v = float(info.get("sell", {}).get("volume", 0))
        summary += f"| {name} | {s:,.2f} | {b:,.2f} | {format_vol(v)} |\n"

    summary += "\n## 🎯 Mission Hub Opportunities (Jita Buy -> Hub Sell)\n"
    summary += "Profit by shipping from Jita or manufacturing locally near the hub.\n\n"
    summary += "| Hub | Item | Jita Buy | Hub Sell | Markup % |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for hub_name, data in hub_data.items():
        for name, tid in MISSION_ESSENTIALS.items():
            j_buy = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
            h_sell = float(data.get(tid, {}).get("sell", {}).get("min", 0))
            if j_buy > 0 and h_sell > 0:
                markup = ((h_sell - j_buy) / j_buy) * 100
                if markup >= 5.0: # Only show significant markups
                    summary += f"| {hub_name} | {name} | {j_buy:,.2f} | {h_sell:,.2f} | **{markup:.1f}%** |\n"

    cat_map = [
        ("🚢 Jita Demand: Ships & Hulls", MFG_SHIPS),
        ("🛰️ Jita Demand: Modules & Fittings", MFG_MODULES),
        ("🔫 Jita Demand: Ammo & Drones", MFG_AMMO),
        ("🔥 Jita High-Demand Essentials", MFG_ESSENTIALS)
    ]
    for header, d in cat_map:
        summary += f"\n## {header}\n"
        summary += "| Item | Jita Sell | Jita Buy | Spread | 24h Vol |\n| :--- | :--- | :--- | :--- | :--- |\n"
        for name, tid in sorted(d.items()):
            info = jita.get(tid, {})
            s = float(info.get("sell", {}).get("min", 0))
            b = float(info.get("buy", {}).get("max", 0))
            v = float(info.get("sell", {}).get("volume", 0))
            if s > 0 and b > 0:
                spread = ((s - b) / b) * 100
                summary += f"| {name} | {s:,.2f} | {b:,.2f} | {spread:.1f}% | {format_vol(v)} |\n"

    summary += "\n\n--- \n*Generated by the Shrimp Market Bot. Includes belt ores and anomaly/escalation types.* 🍤"
    return summary

if __name__ == "__main__":
    report = calculate_spreads()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    report_path = os.path.join(repo_root, "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(report)
    print(f"Analysis complete. Full report synced to {report_path}")
    print(report)
