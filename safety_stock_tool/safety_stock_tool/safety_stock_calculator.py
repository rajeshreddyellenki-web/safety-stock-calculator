"""
Safety Stock Calculator
-----------------------
Calculates safety stock and reorder point for every SKU from past sales and
supplier lead times, then flags items that need reordering.

Formulas (demand and lead time both vary):
  d      = average daily demand
  sigma_d = standard deviation of daily demand
  L      = average lead time (days)
  sigma_L = standard deviation of lead time (days)
  Z      = z-score for the target service level (e.g. 95% -> 1.645)

  Safety stock  = Z * sqrt( L * sigma_d^2  +  d^2 * sigma_L^2 )
  Reorder point = d * L + Safety stock

Usage:
  python safety_stock_calculator.py
  python safety_stock_calculator.py --service-level 0.98 --days 90
  python safety_stock_calculator.py --inventory inventory.csv --sales sales.csv --out report.csv
"""
import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import NormalDist


def parse_date(text):
    return datetime.strptime(text.strip(), "%Y-%m-%d").date()


def load_inventory(path):
    items = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            items.append({
                "sku": row["sku"].strip(),
                "product": row["product"].strip(),
                "category": row["category"].strip(),
                "unit_cost": float(row["unit_cost"]),
                "lead_time_days": float(row["lead_time_days"]),
                "lead_time_std_days": float(row["lead_time_std_days"]),
                "current_stock": int(float(row["current_stock"])),
            })
    return items


def load_sales(path):
    """Return {sku: {date: qty}}"""
    sales = defaultdict(lambda: defaultdict(int))
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sales[row["sku"].strip()][parse_date(row["date"])] += int(float(row["qty"]))
    return sales


def daily_demand_stats(daily_sales, as_of, days):
    """Mean and std dev of daily demand over the last `days` days (days with no sales count as 0)."""
    series = [daily_sales.get(as_of - timedelta(days=i), 0) for i in range(days)]
    mean = statistics.mean(series)
    std = statistics.stdev(series) if len(series) > 1 else 0.0
    return mean, std


def calculate(items, sales, as_of, days, service_level):
    z = NormalDist().inv_cdf(service_level)
    results = []
    for it in items:
        d, sigma_d = daily_demand_stats(sales.get(it["sku"], {}), as_of, days)
        L, sigma_L = it["lead_time_days"], it["lead_time_std_days"]

        safety = z * math.sqrt(L * sigma_d ** 2 + (d ** 2) * (sigma_L ** 2))
        reorder_point = d * L + safety
        safety_u = math.ceil(safety)
        rop_u = math.ceil(reorder_point)

        stock = it["current_stock"]
        if stock <= safety_u:
            status = "CRITICAL"
            action = "Order immediately (at or below safety stock)"
        elif stock <= rop_u:
            status = "REORDER"
            action = "Place order now (below reorder point)"
        else:
            status = "OK"
            action = "No action"

        suggested_order = max(0, rop_u + math.ceil(d * L) - stock) if status != "OK" else 0

        results.append({
            "sku": it["sku"],
            "product": it["product"],
            "category": it["category"],
            "avg_daily_demand": round(d, 2),
            "demand_std_dev": round(sigma_d, 2),
            "lead_time_days": L,
            "lead_time_std_days": sigma_L,
            "safety_stock": safety_u,
            "reorder_point": rop_u,
            "current_stock": stock,
            "safety_stock_value": round(safety_u * it["unit_cost"], 2),
            "status": status,
            "suggested_order_qty": suggested_order,
            "recommended_action": action,
        })
    return results, z


def print_summary(results, service_level, z, top):
    counts = defaultdict(int)
    for r in results:
        counts[r["status"]] += 1
    total_ss_value = sum(r["safety_stock_value"] for r in results)

    print("=" * 66)
    print("SAFETY STOCK REPORT")
    print("=" * 66)
    print(f"Service level: {service_level:.1%}   (Z = {z:.3f})")
    print(f"SKUs analysed: {len(results)}")
    print(f"Total safety stock investment: {total_ss_value:,.2f}")
    print(f"CRITICAL: {counts['CRITICAL']}   REORDER: {counts['REORDER']}   OK: {counts['OK']}")

    urgent = [r for r in results if r["status"] != "OK"]
    urgent.sort(key=lambda r: (r["status"] != "CRITICAL", r["current_stock"] - r["safety_stock"]))
    urgent = urgent[:top]
    if urgent:
        print(f"\nTop {len(urgent)} items needing attention:")
        print(f"{'SKU':<10}{'Status':<10}{'Stock':>7}{'Safety':>8}{'ROP':>7}{'Order qty':>11}")
        for r in urgent:
            print(f"{r['sku']:<10}{r['status']:<10}{r['current_stock']:>7}"
                  f"{r['safety_stock']:>8}{r['reorder_point']:>7}{r['suggested_order_qty']:>11}")


def write_report(results, path):
    order = {"CRITICAL": 0, "REORDER": 1, "OK": 2}
    results = sorted(results, key=lambda r: (order[r["status"]], r["sku"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\nFull report saved to {path}")


def main():
    p = argparse.ArgumentParser(description="Safety Stock Calculator")
    p.add_argument("--inventory", default="inventory.csv")
    p.add_argument("--sales", default="sales.csv")
    p.add_argument("--out", default="safety_stock_report.csv")
    p.add_argument("--service-level", type=float, default=0.95,
                   help="target service level between 0.5 and 0.999 (default 0.95)")
    p.add_argument("--days", type=int, default=90, help="days of sales history to analyse")
    p.add_argument("--as-of", default=None, help="analysis date YYYY-MM-DD (default: today)")
    p.add_argument("--top", type=int, default=10, help="how many urgent items to print")
    args = p.parse_args()

    if not 0.5 <= args.service_level < 1:
        sys.exit("--service-level must be between 0.5 and 0.999")

    as_of = parse_date(args.as_of) if args.as_of else date.today()
    try:
        items = load_inventory(args.inventory)
        sales = load_sales(args.sales)
    except FileNotFoundError as e:
        sys.exit(f"File not found: {e.filename}. Run generate_sample_data.py first.")

    results, z = calculate(items, sales, as_of, args.days, args.service_level)
    print_summary(results, args.service_level, z, args.top)
    write_report(results, args.out)


if __name__ == "__main__":
    main()
