# app.py
import pandas as pd
import streamlit as st

from storage_scraper import scrape_city_market
from kpis import compute_market_kpis, price_comparison_fig

st.set_page_config(page_title="Self-Storage Market Analyzer", layout="wide")
st.title("Self-Storage Market Analyzer (Storage.com Data)")

st.markdown(
    "Type your request below. The app will fetch competitor prices from "
    "Storage.com, build a dataset, and compute revenue-focused KPIs."
)

col_in1, col_in2 = st.columns(2)
with col_in1:
    state = st.text_input("State (as word, like 'california' or 'indiana')", "california")
    city = st.text_input("City slug (as in URL, like 'san-diego')", "san-diego")
with col_in2:
    unit_size = st.selectbox("Unit size (for analysis label)", ["5x5", "10x10", "10x20"], index=1)
    my_price = st.number_input("Your current monthly price ($)", min_value=0.0, value=185.0)
    est_units = st.number_input("Number of units of this type", min_value=1, value=20)

zip_code = st.text_input("ZIP code (optional, for reporting)", "92101")

if st.button("Analyze my market"):
    with st.spinner("Fetching competitor data from Storage.com..."):
        rows = scrape_city_market(state, city, zip_code=zip_code, unit_size=unit_size)
        df = pd.DataFrame(rows)

    if df.empty:
        st.error("No listings found or selectors not configured yet.")
    else:
        st.success(f"Collected {len(df)} competitor listings from Storage.com.")

        st.subheader("1. Raw dataset from Storage.com")
        st.dataframe(df)

        st.subheader("2. KPIs and Revenue Impact")
        kpis = compute_market_kpis(df, my_price, est_units=est_units)

        col1, col2, col3 = st.columns(3)
        col1.metric("Market avg price", f"${kpis['market_avg']:.0f}")
        col2.metric("Your price gap", f"${kpis['price_gap']:.0f}", f"{kpis['price_gap_pct']:.1f}%")
        col3.metric("Promo pressure in market", f"{kpis['promo_pressure']:.1f}%")

        col4, col5 = st.columns(2)
        col4.metric("Demand / occupancy index", f"{kpis['occ_index']:.1f} / 100")
        col5.metric("Recommended price", f"${kpis['recommended_price']:.0f}")

        st.metric(
            "Estimated annual revenue uplift",
            f"${kpis['annual_uplift']:,.0f}",
            help="If you move to the recommended price for this unit size."
        )

        st.subheader("3. Visualization example: price comparison")
        fig = price_comparison_fig(df, my_price)
        st.pyplot(fig)

        st.subheader("4. Narrative summary for the operator")
        if kpis["price_gap"] > 0:
            st.write(
                f"Based on Storage.com listings for {unit_size} units in {city.title()}, {state.title()}, "
                f"your price (${my_price:.0f}) is **below** the market average (${kpis['market_avg']:.0f}). "
                f"With a demand index of {kpis['occ_index']:.1f}, you can move toward the recommended price "
                f"of about ${kpis['recommended_price']:.0f} without losing competitiveness. "
                f"This single adjustment could add roughly **${kpis['annual_uplift']:,.0f} per year** "
                "for this unit type alone."
            )
        else:
            st.write(
                f"Your current price (${my_price:.0f}) is at or above the market average "
                f"(${kpis['market_avg']:.0f}) on Storage.com. Given the current promo pressure "
                f"of {kpis['promo_pressure']:.1f}%, it may be better to hold your price and focus on "
                "amenities and service rather than increasing it further."
            )
