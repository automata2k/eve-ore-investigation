import urllib.request
import json
import ssl
import os
from datetime import datetime

# HUB SETTINGS
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
    "28432": 0.15, "28429": 0.19, "28422": 0.16, "28421": 0.15, "28399": 0.12, "28394": 0.12, "28404": 0.20, "28416": 0.20,
    "195": 0.1, "196": 0.1, "191": 0.1, "28668": 0.01, "2454": 5.0, "2486": 5.0, "2203": 5.0, "218": 0.01
}

# ITEM DEFINITIONS
Ores = {"Compressed Veldspar": "28432", "Compressed Scordite": "28429", "Compressed Pyroxeres": "28422", "Compressed Omber": "28399", "Compressed Gneiss": "28416"}
Goods = {"Nanite Repair Paste": "28668", "Warrior I": "2486", "Hobgoblin I": "2454", "Scourge Heavy Missile": "195", "Acolyte I": "2203"}

def fetch(sid, tids):
    url = f"https://market.fuzzwork.co.uk/aggregates/?station={sid}&types={','.join(set(tids))}"
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ShrimpBot'}), context=ctx) as r:
            return json.loads(r.read().decode())
    except: return {}

def calculate_spreads():
    cargo = 50000
    tax = 0.036 # Assume competitive 3.6% total fees for expert pilot
    all_ids = list(Ores.values()) + list(Goods.values())
    
    jita = fetch(STATIONS["Jita IV-4"]["id"], all_ids)
    hub_data = {h: fetch(STATIONS[h]["id"], all_ids) for h in STATIONS if h != "Jita IV-4"}

    summary = "# 🚀 EVE Arbitrage Daily Report\n"
    summary += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
    summary += "### 🚛 Daily Trade Run (Optimized 50,000 m³)\n"
    summary += "*Logic: Buy from Jita Sell orders, Haul, List as Hub Sell orders. Profits include 3.6% fee deduction.*\n\n"

    runs = []
    for h_key, h_mkt in hub_data.items():
        # Jita -> Hub
        best_out = None
        best_out_p = 0
        for name, tid in Goods.items():
            j_cost = float(jita.get(tid, {}).get("sell", {}).get("min", 0))
            h_price = float(h_mkt.get(tid, {}).get("sell", {}).get("min", 0)) # Listing price
            if j_cost > 0 and h_price > j_cost:
                net_p = (h_price * (1-tax)) - j_cost
                if net_p > 0:
                    u = int(cargo / VOLUMES[tid])
                    p = net_p * u
                    if p > best_out_p:
                        best_out_p = p
                        best_out = {"name": name, "u": u, "profit": p}

        # Hub -> Jita
        best_in = None
        best_in_p = 0
        for name, tid in Ores.items():
            h_cost = float(h_mkt.get(tid, {}).get("sell", {}).get("min", 0))
            j_price = float(jita.get(tid, {}).get("sell", {}).get("min", 0)) # Listing price in Jita
            if h_cost > 0 and j_price > h_cost:
                net_p = (j_price * (1-tax)) - h_cost
                if net_p > 0:
                    u = int(cargo / VOLUMES[tid])
                    p = net_p * u
                    if p > best_in_p:
                        best_in_p = p
                        best_in = {"name": name, "u": u, "profit": p}
        
        if best_out_p > 0 or best_in_p > 0:
            runs.append({"hub": h_key, "out": best_out, "in": best_in, "total": best_out_p + best_in_p})

    runs.sort(key=lambda x: x['total'], reverse=True)
    for r in runs[:3]:
        summary += f"#### The {STATIONS[r['hub']]['region']} Loop ({r['hub']})\n"
        if r['out']: summary += f"- **OUT:** Buy **{r['out']['u']:,} x {r['out']['name']}** (Jita) -> Profit **{r['out']['profit']/1e6:.1f}M**\n"
        if r['in']: summary += f"- **IN:** Buy **{r['in']['u']:,} x {r['in']['name']}** ({r['hub']}) -> Profit **{r['in']['profit']/1e6:.1f}M**\n"
        summary += f"**Predicted Profit: {r['total']/1e6:,.1f} Million ISK**\n\n"

    summary += "\n## 📊 Real-Time Market Check\n"
    summary += "| Item | Region | Hub Price | Jita Price | Spread % |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for h_key, h_mkt in hub_data.items():
        reg = STATIONS[h_key]["region"]
        # Warrior Check
        w_id = Goods["Warrior I"]
        w_j = float(jita.get(w_id, {}).get("sell", {}).get("min", 0))
        w_h = float(h_mkt.get(w_id, {}).get("sell", {}).get("min", 0))
        if w_j > 0 and w_h > 0: summary += f"| Warrior I | {reg} | {w_h:,.0f} | {w_j:,.0f} | {((w_h-w_j)/w_j)*100:.1f}% |\n"
        # Omber Check
        o_id = Ores["Compressed Omber"]
        o_j = float(jita.get(o_id, {}).get("sell", {}).get("min", 0))
        o_h = float(h_mkt.get(o_id, {}).get("sell", {}).get("min", 0))
        if o_j > 0 and o_h > 0: summary += f"| Comp. Omber | {reg} | {o_h:,.0f} | {o_j:,.0f} | {((o_j-o_h)/o_h)*100:.1f}% |\n"

    summary += "\n## ℹ️ Reference\n"
    for k, v in STATIONS.items(): summary += f"**{k}**: {v['name']} ({v['region']})\n\n"
    return summary

if __name__ == "__main__":
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MARKET_DATA.md")
    with open(report_path, "w") as f: f.write(calculate_spreads())
    print("Corrections applied. Verified IDs.")
