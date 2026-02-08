import urllib.request
import json
import ssl
import os
from datetime import datetime

# REGION IDs
REGIONS = {
    "The Forge": "10000002",
    "Domain": "10000043",
    "Sinq Laison": "10000032"
}

# ITEM DEFINITIONS
Ores = {
    "Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422",
    "Compressed Plagioclase": "28421", "Compressed Omber": "28399", "Compressed Kernite": "28394"
}

Goods = {
    "Antimatter Charge M": "218", "Scourge Heavy Missile": "195", "Hobgoblin I": "2454",
    "Warrior I": "2486", "Damage Control I": "520", "Drone Damage Amplifier I": "23559",
    "1600mm Steel Plates I": "11299", "Medium Shield Extender I": "380", "Venture": "32880"
}

def fetch_tycoon_stats(region_id, type_id):
    url = f"https://evetycoon.com/api/v1/market/stats/{region_id}/{type_id}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Mfg-Analyzer-Tycoon'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def generate_report():
    # 1. PRE-FETCH JITA (The Forge)
    jita_mkt = {name: fetch_tycoon_stats(REGIONS["The Forge"], tid) for name, tid in {**Ores, **Goods}.items()}
    
    summary = "# 🛠️ Jita Manufacturing vs. Hauling Analysis (Tycoon Verified)\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "Comparing Regional Hauling profit vs. Jita Local Manufacturing using EVE Tycoon API data.\n\n"

    # 1. HAULING ROI
    summary += "## 📈 Strategy A: Haul & Sell Raw Ore\n"
    summary += "- Buy at Regional Hub min sell, Sell at Jita (The Forge) max buy.\n\n"
    summary += "| Ore Type | Origin Hub | Regional Cost | Jita Buy Order | Margin % |\n| :--- | :--- | :--- | :--- | :--- |\n"
    
    best_ore_val = -100
    best_ore_text = "None"
    
    for h_name in ["Domain", "Sinq Laison"]:
        rid = REGIONS[h_name]
        for name, tid in Ores.items():
            h_cost = float(fetch_tycoon_stats(rid, tid).get("minSell", 0))
            j_gain = float(jita_mkt[name].get("maxBuy", 0))
            
            if h_cost > 0 and j_gain > 0:
                spread = ((j_gain - h_cost) / h_cost) * 100
                if spread > 2:
                    summary += f"| {name} | {h_name} | {h_cost:,.2f} | {j_gain:,.2f} | **{spread:.1f}%** |\n"
                    if spread > best_ore_val:
                        best_ore_val = spread
                        best_ore_text = f"{name} from {h_name} ({spread:.1f}%)"

    # 2. MANUFACTURING ROI
    summary += "\n## 🏗️ Strategy B: Manufacture for Jita\n"
    summary += "- Profit based on 'Sell Average' vs 'Buy Average' in The Forge region (3.6% fees included).\n\n"
    summary += "| Item | Jita Sell | Jita Buy | Net Spread % |\n| :--- | :--- | :--- | :--- |\n"
    
    best_mfg_val = -100
    best_mfg_text = "None"
    tax = 0.036
    
    for name, tid in Goods.items():
        data = jita_mkt[name]
        s = float(data.get("minSell", 0))
        b = float(data.get("maxBuy", 0))
        if s > 0 and b > 0:
            # ROI: (Sell * 0.964) / Buy - 1
            spread = (((s * (1 - tax)) / b) - 1) * 100
            if data.get("sellVolume", 0) > 100:
                summary += f"| {name} | {s:,.2f} | {b:,.2f} | **{spread:.1f}%** |\n"
                if spread > best_mfg_val:
                    best_mfg_val = spread
                    best_mfg_text = f"{name} ({spread:.1f}%)"

    # 3. VERDICT
    summary += "\n## 🍤 Shrimp's Weekly Verdict\n"
    if best_mfg_val > (best_ore_val + 5):
        summary += f"**VERDICT: MANUFACTURE.** Jita manufacturing (**{best_mfg_text}**) is significantly more profitable than regional hauling right now.\n"
    else:
        summary += f"**VERDICT: HAUL ORE.** Hauling **{best_ore_text}** is safer and offers comparable or better ROI for your capital.\n"

    return summary

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, "JITA_MFG_ANALYSIS.md")
    with open(target_path, "w") as f: f.write(generate_report())
    print("Tycoon Manufacturing Analysis Generated.")
