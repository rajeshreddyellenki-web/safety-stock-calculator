"""Generate sample inventory.csv and sales.csv for testing the Safety Stock Calculator."""
import csv
import random
from datetime import date, timedelta

random.seed(7)

CATEGORIES = ["Electronics", "Grocery", "Clothing", "Home", "Toys", "Stationery"]
NUM_PRODUCTS = 40
HISTORY_DAYS = 180
TODAY = date.today()

products = []
for i in range(1, NUM_PRODUCTS + 1):
    products.append({
        "sku": f"SKU{i:04d}",
        "product": f"Product {i}",
        "category": random.choice(CATEGORIES),
        "unit_cost": round(random.uniform(2, 200), 2),
        "lead_time_days": random.randint(3, 21),
        "lead_time_std_days": round(random.uniform(0.5, 4), 1),
        "current_stock": random.randint(0, 400),
    })

with open("inventory.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(products[0].keys()))
    w.writeheader()
    w.writerows(products)

rows = []
for p in products:
    base = random.uniform(1, 12)          # average units per day
    volatility = random.uniform(0.2, 1.2)  # how erratic demand is
    for d in range(HISTORY_DAYS):
        qty = max(0, round(random.gauss(base, base * volatility)))
        if qty > 0:
            rows.append({
                "date": (TODAY - timedelta(days=d)).isoformat(),
                "sku": p["sku"],
                "qty": qty,
            })

rows.sort(key=lambda r: r["date"])
with open("sales.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["date", "sku", "qty"])
    w.writeheader()
    w.writerows(rows)

print(f"Created inventory.csv ({len(products)} products) and sales.csv ({len(rows)} sales rows)")
