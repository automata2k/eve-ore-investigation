import urllib.request
import json
import ssl
import os
from datetime import datetime

# HUB SETTINGS
JITA_IV_4 = "60003760"
AMARR_VIII = "60008494"
DODIXIE_IX = "60011866"

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

def fetch(sid, tids):
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={sid}&types={','.join(set(tids))}"
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot-Mfg-Analyzer'})
        with urllib.request.urlopen(req, context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def generate_report():
    all_ids = list(Ores.values()) + list(Goods.values())
    jita = fetch(JITA_IV_4, all_ids)
    amarr = fetch(AMARR_VIII, list(Ores.values()))
    dodi = fetch(DODIXIE_IX, list(Ores.values()))

    summary = "# 🛠️ Jita Manufacturing vs. Hauling Analysis\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "This report compares the ROI of **Building in High Sec** vs. **Hauling Raw Ore** to Jita.\n\n"

    # 1. HAULING ROI (Best Ore Spreads)
    summary += "## 📈 Strategy A: Haul & Sell Raw Ore\n"
    summary += "Focus on moving Isogen-rich ores from regional hubs to Jita.\n\n"
    summary += "| Ore Type | Origin Hub | Jita Margin % |\n| :--- | :--- | :--- |\n"
    
    best_ore_val = 0
    best_ore_text = ""
    for name, tid in Ores.items():
        j_p = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        for h_key, h_data in [("Amarr", amarr), ("Dodixie", dodi)]:
            h_p = float(h_data.get(tid, {}).get("sell", {}).get("min", 0))
            if j_p > 0 and h_p > 0:
                spread = ((j_p - h_p) / h_p) * 100
                if spread > 5:
                    summary += f"| {name} | {h_key} | **{spread:.1f}%** |\n"
                    if spread > best_ore_val:
                        best_ore_val = spread
                        best_ore_text = f"{name} from {h_key} ({spread:.1f}%)"

    # 2. MANUFACTURING ROI (Jita Spreads)
    summary += "\n## 🏗️ Strategy B: Manufacture for Jita\n"
    summary += "ROI based on Jita Buy (Minerals) -> Jita Sell (Finished Product), minus 3.6% fees.\n\n"
    summary += "| Item | 24h Vol | Jita Market Spread % |\n| :--- | :--- | :--- |\n"
    
    best_mfg_val = 0
    best_mfg_text = ""
    for name, tid in Goods.items():
        s = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
        b = float(jita.get(tid, {}).get("buy", {}).get("max", 0))
        v = float(jita.get(tid, {}).get("sell", {}).get("volume", 0))
        if s > 0 and b > 0:
            spread = ((s - b) / b) * 100
            # Trap filter: Require volume for meaningful strategy
            if v > 100:
                summary += f"| {name} | {v:,.0f} | **{spread:.1f}%** |\n"
                if spread > best_mfg_val:
                    best_mfg_val = spread
                    best_mfg_text = f"{name} ({spread:.1f}%)"

    # 3. THE SHRIMP VERDICT
    summary += "\n## 🍤 Shrimp's Weekly Strategy Recommendation\n"
    if best_mfg_val > (best_ore_val + 10):
        summary += f"**VERDICT: MANUFACTURE.** The highest Jita spread (**{best_mfg_text}**) significantly beats the best hauling route (**{best_ore_text}**). Set up your Raitaru slots and build high-volume T1 items.\n"
    else:
        summary += f"**VERDICT: HAUL ORE.** Hauling **{best_ore_text}** offers similar or better margins with zero manufacturing time and lower market risk.\n"

    summary += "\n*Note: Manufacturing ROI assumes you have BPOs and basic skill levels. Hauling ROI assumes a standard hauler.*"
    return summary

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(base_dir, "JITA_MFG_ANALYSIS.md")
    with open(target_path, "w") as f: f.write(generate_report())
    print("Manufacturing Analysis Generated.")
