# Shield Tanking Theory & Calculation

A guide for calculating Effective DPS (eDPS) tanking capability against New Eden threats.

## 1. The Core Formula

To calculate how much raw incoming damage your active shield build can tank, use the following formula:

**eDPS = Repair Rate (HP/s) / (1 - Average Resistance)**

*   **Repair Rate (HP/s):** The raw amount of shield HP your booster restores per second.
*   **Average Resistance:** Your uniform resistance across all damage types (expressed as a decimal, e.g., 0.75 for 75%).

---

## 2. Example Calculation

**Building Stats:**
- Shield Repair Rate: 134 HP/s
- Average Resistance: 71% (0.71)

**The Math:**
- Inverse Resistance: 1 - 0.71 = 0.29
- eDPS: 134 / 0.29 = **462.06 eDPS**

*This build can neutralize ~462 raw DPS from enemies indefinitely, assuming the capacitor remains stable.*

---

## 3. Targeting the "God Tank" (1,000 eDPS)

To hit the legendary 1,000 eDPS milestone, you must focus on the relationship between raw repair and resistance:

| If your Repair Rate is... | You need average Resists of... | Result |
| :--- | :--- | :--- |
| **134 HP/s** | 86.6% | 1,000 eDPS |
| **200 HP/s** | 80.0% | 1,000 eDPS |
| **250 HP/s** | 75.0% | 1,000 eDPS |
| **300 HP/s** | 70.0% | 1,000 eDPS |

---

## 4. Practical Application

### Resistance Holes
Against Sleepers or specialized PvP fits, your tank is only as strong as your **weakest** resist. If you have 80% Omni resists but a 0% hole in EM, an EM-focused attacker will effectively ignore your "Omni" calculation and shred you.

### Capacitor Efficiency
Active tanking is a race against your capacitor. Always prioritize **Cap Battery** modules or **Capacitor Control Circuit** rigs when attempting to maintain high-eDPS tanks for long durations (e.g., soloing Class 3 sites).

---
*Reference: Strategic Defense Manual 2026*
