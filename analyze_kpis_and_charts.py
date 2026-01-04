# analyze_kpis_and_charts.py
#
# 1. Loads the CSV produced by build_dataset_from_html.py
# 2. Computes market KPIs and a rough revenue uplift estimate
# 3. Saves multiple charts that you can use in your presentation

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

CSV_PATH = Path("C:\\Users\\divay\\Desktop\\cubby_diagram\\storage_market_indianapolis.csv")

# Output image paths
PRICE_COMPARISON_PNG = Path("price_comparison.png")
PRICE_HISTOGRAM_PNG = Path("price_histogram.png")
PRICE_DISTANCE_PNG = Path("price_vs_distance.png")
RATING_PRICE_PNG = Path("rating_vs_price.png")
PROMO_PRESSURE_PNG = Path("promo_pressure.png")
REVENUE_UPLIFT_PNG = Path("revenue_uplift.png")
OPPORTUNITY_QUADRANT_PNG = Path("opportunity_quadrant.png")
RATING_PROMO_MATRIX_PNG = Path("rating_promo_matrix.png")

# Demo parameters – adjust for your story
MY_FACILITY_NAME = "My Facility"
MY_PRICE = 60.0          # your current price for this unit type
EST_UNITS = 20           # how many such units you have (for revenue uplift calc)


# -------------------------------------------------------------------
# KPI COMPUTATION
# -------------------------------------------------------------------

def compute_market_kpis(df: pd.DataFrame, my_price: float, est_units: int = 20) -> dict:
    """Compute simple KPIs from the market listing dataset."""
    df = df.copy().dropna(subset=["lowest_price"])

    market_avg = df["lowest_price"].mean()
    market_min = df["lowest_price"].min()
    market_max = df["lowest_price"].max()

    price_gap = market_avg - my_price
    price_gap_pct = (price_gap / market_avg * 100) if market_avg else 0.0

    # Promo pressure = share of competitors with a discount
    promo_pressure = df["promo_flag"].mean() * 100

    # Simple demand / occupancy index based on price level and promo usage
    def demand_score(row):
        if row["lowest_price"] >= market_avg and not row["promo_flag"]:
            return 1.0       # high demand, no discount
        elif row["lowest_price"] >= market_avg and row["promo_flag"]:
            return 0.8
        elif row["lowest_price"] < market_avg and not row["promo_flag"]:
            return 0.7
        else:
            return 0.5       # cheap + discounted = weaker demand

    df["demand_signal"] = df.apply(demand_score, axis=1)
    occ_index = df["demand_signal"].mean() * 100  # 0–100 scale

    # Recommended price: at least the market average if you are below it
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
    }


# -------------------------------------------------------------------
# FIGURE HELPERS
# -------------------------------------------------------------------

def price_comparison_fig(df: pd.DataFrame, my_price: float, my_label: str = "My Facility"):
    """Bar chart comparing competitor prices with your price."""
    df_plot = df.copy().dropna(subset=["lowest_price"])

    labels = df_plot["facility_name"].tolist() + [my_label]
    prices = df_plot["lowest_price"].tolist() + [my_price]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(range(len(prices)), prices)
    ax.set_xticks(range(len(prices)))
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("Lowest monthly price ($)")
    ax.set_title("Storage.com Competitor Price Comparison")
    fig.tight_layout()
    return fig


def price_histogram_fig(df: pd.DataFrame):
    """Histogram showing the distribution of competitor prices."""
    df_plot = df.copy().dropna(subset=["lowest_price"])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(df_plot["lowest_price"], bins=10)
    ax.set_xlabel("Lowest monthly price ($)")
    ax.set_ylabel("Number of competitors")
    ax.set_title("Market Price Distribution")
    fig.tight_layout()
    return fig


def price_vs_distance_fig(df: pd.DataFrame, my_price: float, my_label: str = "My Facility"):
    """Scatterplot of price vs distance."""
    df_plot = df.copy().dropna(subset=["lowest_price", "distance_miles"])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(df_plot["distance_miles"], df_plot["lowest_price"], alpha=0.7)
    ax.set_xlabel("Distance from search center (miles)")
    ax.set_ylabel("Lowest monthly price ($)")
    ax.set_title("Price vs Distance")

    # Optionally plot your facility at distance 0 for illustration
    ax.scatter([0], [my_price], marker="*", s=120)
    ax.annotate(my_label, (0, my_price), textcoords="offset points", xytext=(5, 5))
    fig.tight_layout()
    return fig


def rating_vs_price_fig(df: pd.DataFrame, my_price: float, my_label: str = "My Facility"):
    """Scatterplot of rating vs price (value positioning)."""
    df_plot = df.copy().dropna(subset=["lowest_price", "rating"])

    fig, ax = plt.subplots(figsize=(6, 4))
    sizes = (df_plot["rating_count"].fillna(0) + 1) * 2  # bubble size
    ax.scatter(df_plot["rating"], df_plot["lowest_price"], s=sizes, alpha=0.7)
    ax.set_xlabel("Rating (stars)")
    ax.set_ylabel("Lowest monthly price ($)")
    ax.set_title("Rating vs Price (Value Positioning)")

    # Plot your facility at a hypothetical rating (e.g., 4.7)
    my_rating = 4.7
    ax.scatter([my_rating], [my_price], marker="*", s=120)
    ax.annotate(my_label, (my_rating, my_price), textcoords="offset points", xytext=(5, 5))
    fig.tight_layout()
    return fig


def promo_pressure_fig(df: pd.DataFrame):
    """Bar chart showing share of competitors with and without promos."""
    df_plot = df.copy()
    promo_share = df_plot["promo_flag"].mean()
    no_promo_share = 1 - promo_share

    labels = ["With promo", "No promo"]
    values = [promo_share * 100, no_promo_share * 100]

    fig, ax = plt.subplots(figsize=(4, 4))
    ax.bar(labels, values)
    ax.set_ylabel("Share of competitors (%)")
    ax.set_title("Promo Pressure in Market")
    fig.tight_layout()
    return fig


def revenue_uplift_fig(my_price: float, kpis: dict, est_units: int):
    """Bar chart comparing current vs potential annual revenue."""
    current_annual = my_price * est_units * 12
    potential_annual = kpis["recommended_price"] * est_units * 12

    labels = ["Current price", "Recommended price"]
    values = [current_annual, potential_annual]

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(labels, values)
    ax.set_ylabel("Annual revenue ($)")
    ax.set_title("Revenue Impact of Price Optimization")
    fig.tight_layout()
    return fig


def opportunity_quadrant_fig(df: pd.DataFrame, my_price: float, my_label: str = "My Facility"):
    """
    Scatter of price deviation from market vs demand signal.
    Shows where competitors (and you) fall in opportunity space.
    """
    df_plot = df.copy().dropna(subset=["lowest_price"])
    market_avg = df_plot["lowest_price"].mean()

    # Rebuild demand_signal similar to KPI function
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
    df_plot["price_deviation"] = df_plot["lowest_price"] - market_avg

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(df_plot["price_deviation"], df_plot["demand_signal"], alpha=0.7)
    ax.axvline(0, color="gray", linestyle="--", linewidth=1)
    ax.axhline(df_plot["demand_signal"].mean(), color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("Price deviation from market avg ($)")
    ax.set_ylabel("Demand / occupancy signal (0–1)")
    ax.set_title("Opportunity Quadrant: Price vs Demand")

    # Plot your facility at deviation = my_price - market_avg, demand ~ mean
    my_dev = my_price - market_avg
    my_demand = df_plot["demand_signal"].mean()
    ax.scatter([my_dev], [my_demand], marker="*", s=120)
    ax.annotate(my_label, (my_dev, my_demand), textcoords="offset points", xytext=(5, 5))

    fig.tight_layout()
    return fig


def rating_promo_matrix_fig(df: pd.DataFrame):
    """
    Bar chart: rating buckets vs promo usage share.
    Buckets: <4.0, 4.0–4.5, >4.5
    """
    df_plot = df.copy().dropna(subset=["rating"])

    def bucket(r):
        if r < 4.0:
            return "<4.0★"
        elif r <= 4.5:
            return "4.0–4.5★"
        else:
            return ">4.5★"

    df_plot["rating_bucket"] = df_plot["rating"].apply(bucket)

    grouped = df_plot.groupby("rating_bucket")["promo_flag"].mean() * 100
    buckets = grouped.index.tolist()
    values = grouped.values.tolist()

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(buckets, values)
    ax.set_ylabel("Share with promos (%)")
    ax.set_title("Promo Usage by Rating Bucket")
    fig.tight_layout()
    return fig


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV not found: {CSV_PATH.resolve()} – run build_dataset_from_html.py first."
        )

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} competitors from {CSV_PATH.name}")

    kpis = compute_market_kpis(df, MY_PRICE, est_units=EST_UNITS)

    print("\n=== Market KPIs (from Storage.com dataset) ===")
    print(f"Market avg price:     ${kpis['market_avg']:.2f}")
    print(f"Market min price:     ${kpis['market_min']:.2f}")
    print(f"Market max price:     ${kpis['market_max']:.2f}")
    print(f"Your price gap:       ${kpis['price_gap']:.2f} ({kpis['price_gap_pct']:.1f}%)")
    print(f"Promo pressure:       {kpis['promo_pressure']:.1f}% of competitors use promos")
    print(f"Demand / occ. index:  {kpis['occ_index']:.1f} / 100")

    print("\n=== Revenue impact ===")
    print(f"Recommended price:    ${kpis['recommended_price']:.2f}")
    print(
        f"Estimated annual uplift if you move to recommended price "
        f"(for {EST_UNITS} units): ${kpis['annual_uplift']:,.0f}"
    )

    # 1) Price comparison
    fig = price_comparison_fig(df, MY_PRICE, MY_FACILITY_NAME)
    fig.savefig(PRICE_COMPARISON_PNG, dpi=150, bbox_inches="tight")
    print(f"\nSaved price comparison chart to: {PRICE_COMPARISON_PNG.resolve()}")

    # 2) Market price histogram
    fig = price_histogram_fig(df)
    fig.savefig(PRICE_HISTOGRAM_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved price histogram to: {PRICE_HISTOGRAM_PNG.resolve()}")

    # 3) Price vs distance scatter
    fig = price_vs_distance_fig(df, MY_PRICE, MY_FACILITY_NAME)
    fig.savefig(PRICE_DISTANCE_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved price vs distance chart to: {PRICE_DISTANCE_PNG.resolve()}")

    # 4) Rating vs price scatter
    fig = rating_vs_price_fig(df, MY_PRICE, MY_FACILITY_NAME)
    fig.savefig(RATING_PRICE_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved rating vs price chart to: {RATING_PRICE_PNG.resolve()}")

    # 5) Promo pressure bar chart
    fig = promo_pressure_fig(df)
    fig.savefig(PROMO_PRESSURE_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved promo pressure chart to: {PROMO_PRESSURE_PNG.resolve()}")

    # 6) Revenue uplift bar chart
    fig = revenue_uplift_fig(MY_PRICE, kpis, EST_UNITS)
    fig.savefig(REVENUE_UPLIFT_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved revenue uplift chart to: {REVENUE_UPLIFT_PNG.resolve()}")

    # 7) Opportunity quadrant chart
    fig = opportunity_quadrant_fig(df, MY_PRICE, MY_FACILITY_NAME)
    fig.savefig(OPPORTUNITY_QUADRANT_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved opportunity quadrant chart to: {OPPORTUNITY_QUADRANT_PNG.resolve()}")

    # 8) Rating vs promo matrix
    fig = rating_promo_matrix_fig(df)
    fig.savefig(RATING_PROMO_MATRIX_PNG, dpi=150, bbox_inches="tight")
    print(f"Saved rating-promo matrix chart to: {RATING_PROMO_MATRIX_PNG.resolve()}")


if __name__ == "__main__":
    main()
