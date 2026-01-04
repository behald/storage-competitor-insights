# build_dataset_from_html.py
#
# 1. Loads a saved Storage.com search results page (HTML file)
# 2. Extracts facility data (name, address, prices, rating, distance, promo)
# 3. Saves the result as a CSV for KPI analysis and visualization

import json
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

HTML_PATH = Path("www.storage.com.html")        # put the file in same folder as this script
OUTPUT_CSV = Path("storage_market_indianapolis.csv")


def parse_storage_cards_from_html(html: str) -> pd.DataFrame:
    """Parse all <div class="facility-card"> blocks on a Storage.com search page."""
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.facility-card")
    rows = []

    for card in cards:
        # 1) Structured JSON inside each card
        ld_tag = card.find("script", {"type": "application/ld+json"})
        data = {}
        if ld_tag:
            try:
                data = json.loads(ld_tag.get_text(strip=True))
            except Exception:
                data = {}

        name = data.get("name")
        url = data.get("url")
        price_range = data.get("priceRange")

        address = data.get("address") or {}
        if isinstance(address, dict):
            city = address.get("addressLocality")
            state = address.get("addressRegion")
            zip_code = address.get("postalCode")
            street = address.get("streetAddress")
        else:
            city = state = zip_code = street = None

        geo = data.get("geo") or {}
        lat = geo.get("latitude") if isinstance(geo, dict) else None
        lon = geo.get("longitude") if isinstance(geo, dict) else None

        agg = data.get("aggregateRating") or {}
        rating = agg.get("ratingValue") if isinstance(agg, dict) else None
        rating_count = agg.get("ratingCount") if isinstance(agg, dict) else None

        # 2) Extra info from visible HTML

        # Full address text line
        addr_span = card.select_one("span.facility-address")
        addr_text = addr_span.get_text(strip=True) if addr_span else None

        # Distance, e.g. "5 miles"
        dist_span = card.select_one("div.facility-distance span")
        distance_miles = None
        if dist_span:
            txt = dist_span.get_text(strip=True)
            try:
                distance_miles = float(txt.split()[0])
            except Exception:
                pass

        # Prices: lowest (current) price and starting/original price
        lowest_span = card.select_one("span.lowest-price")
        starting_span = card.select_one("span.starting-price")

        lowest_price = None
        starting_price = None

        if lowest_span:
            try:
                lowest_price = float(
                    lowest_span.get_text(strip=True).replace("$", "").replace(",", "")
                )
            except Exception:
                pass

        if starting_span:
            try:
                starting_price = float(
                    starting_span.get_text(strip=True).replace("$", "").replace(",", "")
                )
            except Exception:
                pass

        # We treat "promo" as "there is a crossed-out starting price higher than the lowest price"
        promo_flag = (
            lowest_price is not None
            and starting_price is not None
            and lowest_price < starting_price
        )

        rows.append(
            {
                "facility_name": name,
                "relative_url": url,
                "street": street,
                "city": city,
                "state": state,
                "zip_code": zip_code,
                "address_text": addr_text,
                "distance_miles": distance_miles,
                "lowest_price": lowest_price,
                "starting_price": starting_price,
                "price_range": price_range,
                "promo_flag": promo_flag,
                "rating": rating,
                "rating_count": rating_count,
                "latitude": lat,
                "longitude": lon,
            }
        )

    return pd.DataFrame(rows)


def main():
    if not HTML_PATH.exists():
        raise FileNotFoundError(f"HTML file not found: {HTML_PATH.resolve()}")

    html = HTML_PATH.read_text(encoding="utf-8", errors="ignore")
    df = parse_storage_cards_from_html(html)

    print(f"Parsed {len(df)} facilities from Storage.com")
    print(df.head())

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved dataset to: {OUTPUT_CSV.resolve()}")


if __name__ == "__main__":
    main()
