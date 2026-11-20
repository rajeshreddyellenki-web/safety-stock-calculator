# Safety Stock Calculator

Calculates how much buffer stock each product needs to avoid stockouts, works out the reorder point, and flags items that should be ordered now.

## Files
| File | Purpose |
|---|---|
| `generate_sample_data.py` | Creates sample `inventory.csv` and `sales.csv` |
| `safety_stock_calculator.py` | Main tool: calculates safety stock and reorder points |

## Input format
**inventory.csv**: `sku, product, category, unit_cost, lead_time_days, lead_time_std_days, current_stock`
**sales.csv**: `date (YYYY-MM-DD), sku, qty`

## Run
```
python generate_sample_data.py      # skip if you have your own CSVs
python safety_stock_calculator.py
```
Options: `--service-level 0.95` `--days 90` `--top 10` `--as-of 2026-11-19` `--out report.csv`

## Formulas
- Safety stock = Z x sqrt( L x sigma_d^2 + d^2 x sigma_L^2 )
- Reorder point = d x L + Safety stock

d = average daily demand, sigma_d = std dev of daily demand, L = lead time (days), sigma_L = std dev of lead time, Z = z-score of the target service level (95% = 1.645, 99% = 2.326).

## Status rules
- **CRITICAL**: current stock is at or below safety stock
- **REORDER**: current stock is at or below the reorder point
- **OK**: stock is above the reorder point

Suggested order qty = enough to bring stock back to the reorder point plus one lead time of demand.

## Ideas to extend
- Add a Streamlit dashboard or matplotlib charts
- Use different service levels per category (A/B/C items)
- Add economic order quantity (EOQ) for order sizing
- Forecast demand with moving averages or exponential smoothing
