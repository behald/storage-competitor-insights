import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List

CSV_PATH = Path("C:\\Users\\divay\\Desktop\\cubby_diagram\\storage_market_indianapolis.csv")

# You can change these for your demo
MY_FACILITY_NAME = "My Facility"
MY_PRICE = 60.0    # your current price
EST_UNITS = 20     # number of units of this type


# ----------------------------------------------------
# Basic KPI helper (similar to previous script)
# ----------------------------------------------------

def compute_market_kpis(df: pd.DataFrame, my_price: float, est_units: int) -> Dict:
    df = df.copy().dropna(subset=["lowest_price"])
    market_avg = df["lowest_price"].mean()
    market_min = df["lowest_price"].min()
    market_max = df["lowest_price"].max()

    price_gap = market_avg - my_price
    price_gap_pct = (price_gap / market_avg * 100) if market_avg else 0.0

    promo_pressure = df["promo_flag"].mean() * 100

    def demand_score(row):
        if row["lowest_price"] >= market_avg and not row["promo_flag"]:
            return 1.0
        elif row["lowest_price"] >= market_avg and row["promo_flag"]:
            return 0.8
        elif row["lowest_price"] < market_avg and not row["promo_flag"]:
            return 0.7
        else:
            return 0.5

    df["demand_signal"] = df.apply(demand_score, axis=1)
    occ_index = df["demand_signal"].mean() * 100

    recommended_price = max(my_price, market_avg)
    extra_per_unit = max(0.0, recommended_price - my_price)
    annual_uplift = extra_per_unit * est_units * 12

    return {
        "market_avg": market_avg,
        "market_min": market_min,
        "market_max": market_max,
        "price_gap": price_gap,
        "price_gap_pct": price_gap_pct,
        "promo_pressure": promo_pressure,
        "occ_index": occ_index,
        "recommended_price": recommended_price,
        "annual_uplift": annual_uplift,
        "extra_per_unit": extra_per_unit,
    }


# ----------------------------------------------------
# 1. Money on the Table table
# ----------------------------------------------------

def build_money_on_table(kpis: Dict, my_price: float, est_units: int) -> pd.DataFrame:
    row = {
        "unit_type": "Example unit type",
        "your_price": my_price,
        "market_avg_price": kpis["market_avg"],
        "price_gap": kpis["market_avg"] - my_price,
        "price_gap_pct": kpis["price_gap_pct"],
        "annual_uplift": kpis["annual_uplift"],
        "units": est_units,
    }
    return pd.DataFrame([row])


# ----------------------------------------------------
# 2. Scenario slider: different price changes
# ----------------------------------------------------

def build_scenario_table(kpis: Dict, my_price: float, est_units: int) -> pd.DataFrame:
    # base occupancy as demand index (0–1)
    base_occ = kpis["occ_index"] / 100.0
    if base_occ <= 0:
        base_occ = 0.9

    scenarios: List[Dict] = []
    for pct_change in [-0.10, -0.05, 0.0, 0.03, 0.05, 0.10]:
        new_price = my_price * (1.0 + pct_change)

        # simple assumption: every +5% in price reduces occupancy by 2.5 points
        occ = base_occ - (pct_change * 0.5)
        occ = max(0.6, min(1.0, occ))

        current_revenue = my_price * est_units * 12 * base_occ
        scenario_revenue = new_price * est_units * 12 * occ
        delta_revenue = scenario_revenue - current_revenue

        scenarios.append(
            {
                "price_change_pct": pct_change * 100,
                "new_price": new_price,
                "est_occupancy": occ * 100,
                "est_annual_revenue": scenario_revenue,
                "delta_vs_current": delta_revenue,
            }
        )

    return pd.DataFrame(scenarios)


# ----------------------------------------------------
# 3. Raise / Hold / Defend decision tag
# ----------------------------------------------------

def classify_action(kpis: Dict) -> str:
    gap_pct = kpis["price_gap_pct"]
    occ_index = kpis["occ_index"]
    promo_pressure = kpis["promo_pressure"]

    # Thresholds you can tune
    if gap_pct > 3 and occ_index > 65:
        return "Raise"
    if -3 <= gap_pct <= 3:
        return "Hold"
    if gap_pct < -3 or promo_pressure > 70:
        return "Defend"
    return "Hold"


# ----------------------------------------------------
# 4. Top 10 underpriced competitors (vs market avg)
# ----------------------------------------------------

def top_underpriced_chart(df: pd.DataFrame, output_path: Path):
    df_plot = df.copy().dropna(subset=["lowest_price"])
    market_avg = df_plot["lowest_price"].mean()
    df_plot["underpricing_gap"] = market_avg - df_plot["lowest_price"]
    df_plot = df_plot[df_plot["underpricing_gap"] > 0]
    df_plot = df_plot.sort_values("underpricing_gap", ascending=False).head(10)

    if df_plot.empty:
        print("No underpriced competitors found for Top 10 chart.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(df_plot["facility_name"], df_plot["underpricing_gap"])
    ax.set_xlabel("Underpricing vs market avg ($)")
    ax.set_title("Top 10 Underpriced Competitors (vs Market Avg)")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Top 10 underpriced chart to: {output_path.resolve()}")


# ----------------------------------------------------
# 5. Discount dependence chart (aggregate)
# ----------------------------------------------------

def discount_dependence_chart(df: pd.DataFrame, output_path: Path):
    df_plot = df.copy()

    with_promo = df_plot[df_plot["promo_flag"] & df_plot["starting_price"].notna()]
    no_promo = df_plot[~df_plot["promo_flag"]]

    avg_discounted = with_promo["lowest_price"].mean()
    avg_original = with_promo["starting_price"].mean()
    avg_no_promo = no_promo["lowest_price"].mean()

    labels = ["No promo avg price", "Original price with promo", "Discounted price with promo"]
    values = [avg_no_promo, avg_original, avg_discounted]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values)
    ax.set_ylabel("Monthly price ($)")
    ax.set_title("Discount Dependence Snapshot")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved discount dependence chart to: {output_path.resolve()}")


# ----------------------------------------------------
# 6. Price–rating–opportunity bubble chart
# ----------------------------------------------------

def price_rating_opportunity_chart(df: pd.DataFrame, output_path: Path):
    df_plot = df.copy().dropna(subset=["lowest_price", "rating"])
    if df_plot.empty:
        print("No rating data available for price-rating-opportunity chart.")
        return

    market_avg = df_plot["lowest_price"].mean()
    df_plot["price_gap_vs_market"] = market_avg - df_plot["lowest_price"]

    fig, ax = plt.subplots(figsize=(6, 4))
    sizes = (df_plot["rating_count"].fillna(0) + 1) * 3
    sc = ax.scatter(df_plot["rating"], df_plot["price_gap_vs_market"], s=sizes, alpha=0.7)
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xlabel("Rating (stars)")
    ax.set_ylabel("Gap: market avg - facility price ($)")
    ax.set_title("Price–Rating–Opportunity Bubbles")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved price-rating-opportunity chart to: {output_path.resolve()}")


# ----------------------------------------------------
# 7. Neighborhood profit heatmap (distance band x price band)
# ----------------------------------------------------

def neighborhood_heatmap(df: pd.DataFrame, output_path: Path):
    df_plot = df.copy().dropna(subset=["lowest_price", "distance_miles"])
    if df_plot.empty:
        print("Not enough distance/price data for heatmap.")
        return

    # Distance bands
    def dist_band(d):
        if d <= 2:
            return "0–2 mi"
        elif d <= 4:
            return "2–4 mi"
        elif d <= 6:
            return "4–6 mi"
        else:
            return "6+ mi"

    df_plot["dist_band"] = df_plot["distance_miles"].apply(dist_band)

    # Price bands: cheap / mid / premium via quantiles
    q1 = df_plot["lowest_price"].quantile(0.33)
    q2 = df_plot["lowest_price"].quantile(0.66)

    def price_band(p):
        if p <= q1:
            return "Cheap"
        elif p <= q2:
            return "Mid"
        else:
            return "Premium"

    df_plot["price_band"] = df_plot["lowest_price"].apply(price_band)

    # Use demand_signal as proxy (recompute here)
    market_avg = df_plot["lowest_price"].mean()

    def demand_score(row):
        if row["lowest_price"] >= market_avg and not row["promo_flag"]:
            return 1.0
        elif row["lowest_price"] >= market_avg and row["promo_flag"]:
            return 0.8
        elif row["lowest_price"] < market_avg and not row["promo_flag"]:
            return 0.7
        else:
            return 0.5

    df_plot["demand_signal"] = df_plot.apply(demand_score, axis=1)

    pivot = pd.pivot_table(
        df_plot,
        values="demand_signal",
        index="dist_band",
        columns="price_band",
        aggfunc="mean",
    )

    if pivot.empty:
        print("Pivot for heatmap is empty.")
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(pivot.values, aspect="auto")

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=8)

    ax.set_xlabel("Price band")
    ax.set_ylabel("Distance band")
    ax.set_title("Neighborhood Demand Heatmap (proxy)")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved neighborhood heatmap to: {output_path.resolve()}")


# ----------------------------------------------------
# 8. Promo ROI snapshot (simple scenario table)
# ----------------------------------------------------

def build_promo_roi_table(kpis: Dict, my_price: float, est_units: int) -> pd.DataFrame:
    base_occ = kpis["occ_index"] / 100.0
    if base_occ <= 0:
        base_occ = 0.9

    scenarios = []

    # No promo
    occ_no = base_occ
    rev_no = my_price * est_units * 12 * occ_no
    scenarios.append(
        {
            "scenario": "No promo",
            "price": my_price,
            "effective_discount_pct": 0.0,
            "est_occupancy_pct": occ_no * 100,
            "est_annual_revenue": rev_no,
        }
    )

    # Light promo
    price_light = my_price
    occ_light = min(1.0, base_occ + 0.05)
    rev_light = price_light * est_units * 12 * occ_light
    scenarios.append(
        {
            "scenario": "Light promo",
            "price": price_light,
            "effective_discount_pct": 5.0,
            "est_occupancy_pct": occ_light * 100,
            "est_annual_revenue": rev_light,
        }
    )

    # Heavy promo
    price_heavy = my_price - 5  # flat $5 off for illustration
    occ_heavy = min(1.0, base_occ + 0.10)
    rev_heavy = price_heavy * est_units * 12 * occ_heavy
    scenarios.append(
        {
            "scenario": "Heavy promo",
            "price": price_heavy,
            "effective_discount_pct": (5.0 / my_price) * 100,
            "est_occupancy_pct": occ_heavy * 100,
            "est_annual_revenue": rev_heavy,
        }
    )

    return pd.DataFrame(scenarios)


# ----------------------------------------------------
# 9. Good / Fair / Risky price bands
# ----------------------------------------------------

def price_band_share_chart(df: pd.DataFrame, output_path: Path):
    df_plot = df.copy().dropna(subset=["lowest_price"])
    if df_plot.empty:
        print("No price data for band share chart.")
        return

    market_avg = df_plot["lowest_price"].mean()

    def band(row):
        dev_pct = (row["lowest_price"] - market_avg) / market_avg * 100
        if abs(dev_pct) <= 5:
            return "Good (±5%)"
        elif abs(dev_pct) <= 10:
            return "Fair (5–10%)"
        else:
            return "Risky (>10%)"

    df_plot["price_band"] = df_plot.apply(band, axis=1)
    shares = df_plot["price_band"].value_counts(normalize=True) * 100

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(shares.index, shares.values)
    ax.set_ylabel("Share of competitors (%)")
    ax.set_title("Price Positioning: Good / Fair / Risky vs Market")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved price band share chart to: {output_path.resolve()}")


# ----------------------------------------------------
# 10. Trend-over-time (if multiple scrape_dates exist)
# ----------------------------------------------------

def trend_over_time_chart(df: pd.DataFrame, my_price: float, output_path: Path):
    if "scrape_date" not in df.columns:
        print("No 'scrape_date' column – skipping trend chart.")
        return

    df_plot = df.copy().dropna(subset=["lowest_price"])
    if df_plot["scrape_date"].nunique() < 2:
        print("Only one scrape_date present – need multiple dates for trend chart.")
        return

    # Compute market avg per date
    grouped = df_plot.groupby("scrape_date")["lowest_price"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(grouped["scrape_date"], grouped["lowest_price"], marker="o", label="Market avg price")
    ax.axhline(my_price, linestyle="--", linewidth=1, label="Your price")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price ($)")
    ax.set_title("Market Price vs Your Price Over Time")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved trend-over-time chart to: {output_path.resolve()}")


# ----------------------------------------------------
# MAIN
# ----------------------------------------------------

def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"{CSV_PATH.resolve()} not found. Run build_dataset_from_html.py first.")

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} competitor rows from {CSV_PATH.name}")

    kpis = compute_market_kpis(df, MY_PRICE, EST_UNITS)
    print("\nBasic KPIs:")
    for k, v in kpis.items():
        print(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")

    # 1) Money on the table
    mot_df = build_money_on_table(kpis, MY_PRICE, EST_UNITS)
    mot_path = Path("money_on_table.csv")
    mot_df.to_csv(mot_path, index=False)
    print(f"\nSaved 'Money on the Table' table to: {mot_path.resolve()}")

    # 2) Scenario table
    scen_df = build_scenario_table(kpis, MY_PRICE, EST_UNITS)
    scen_path = Path("price_scenarios.csv")
    scen_df.to_csv(scen_path, index=False)
    print(f"Saved price scenario table to: {scen_path.resolve()}")

    # 3) Raise / Hold / Defend
    decision = classify_action(kpis)
    print(f"\nPricing action suggestion for this unit type: {decision}")

    # 4) Top 10 underpriced competitors chart
    top_underpriced_chart(df, Path("top_underpriced.png"))

    # 5) Discount dependence chart
    discount_dependence_chart(df, Path("discount_dependence.png"))

    # 6) Price–rating–opportunity bubble
    price_rating_opportunity_chart(df, Path("price_rating_opportunity.png"))

    # 7) Neighborhood profit heatmap
    neighborhood_heatmap(df, Path("neighborhood_heatmap.png"))

    # 8) Promo ROI snapshot table
    promo_df = build_promo_roi_table(kpis, MY_PRICE, EST_UNITS)
    promo_path = Path("promo_roi_snapshot.csv")
    promo_df.to_csv(promo_path, index=False)
    print(f"Saved promo ROI snapshot table to: {promo_path.resolve()}")

    # 9) Price band share chart
    price_band_share_chart(df, Path("price_band_share.png"))

    # 10) Trend-over-time chart
    trend_over_time_chart(df, MY_PRICE, Path("market_trend.png"))


if __name__ == "__main__":
    main()
