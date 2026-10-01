import pandas as pd
import numpy as np

np.random.seed(7)

MONTHS = pd.date_range("2025-09-01", periods=12, freq="MS")  # Sep 2025 - Aug 2026

# Top / healthy vendors with annual sales target ($ Millions) and typical margin
TOP_VENDORS = [
    ("Diageo North America Inc", 68, 0.44, ["Capt Morgan Spiced", "Ketel One Vodka", "Baileys Irish Cream", "Tanqueray"]),
    ("Martignetti Companies", 39, 0.41, ["Tito's Handmade Vodka"]),
    ("Pernod Ricard USA", 32, 0.42, ["Absolut 80 Proof", "Jameson Irish Whiskey", "Kahlua"]),
    ("Jim Beam Brands Company", 31, 0.40, ["Jim Beam Bourbon"]),
    ("Bacardi USA Inc", 25, 0.43, ["Grey Goose Vodka", "Bacardi Superior Rum"]),
    ("Constellation Brands", 24, 0.39, ["Corona Extra"]),
    ("E & J Gallo Winery", 18, 0.37, ["Gallo Family Vineyards"]),
    ("Brown-Forman Corp", 18, 0.45, ["Jack Daniel's No. 7"]),
    ("Ultra Beverage Co", 17, 0.36, ["Ultra Craft Lager"]),
    ("M S Walker Inc", 15, 0.38, ["Walker's Reserve Whiskey"]),
]

# Low performing vendors (smaller, weaker margins) -> matches earlier flagged low performers
LOW_VENDORS = [
    ("Dunn Wine Brokers", 6.5, 0.22, ["Dunn Cellar Red"]),
    ("Circa Wines", 5.8, 0.20, ["Circa Chardonnay"]),
    ("Park Street Imports LLC", 7.2, 0.19, ["Park Street Lager"]),
    ("Highland Wine Merchants", 4.9, 0.15, ["Highland Malt Reserve"]),
    ("Alisa Carr Beverages", 4.1, 0.11, ["Alisa Sparkling Rose"]),
]

ALL_VENDORS = TOP_VENDORS + LOW_VENDORS

rows = []
for vendor, annual_sales_m, margin, brands in ALL_VENDORS:
    annual_sales = annual_sales_m * 1_000_000
    # split sales across brands (roughly equal with some noise)
    brand_weights = np.random.dirichlet(np.ones(len(brands)) * 3)
    for brand, bw in zip(brands, brand_weights):
        brand_annual_sales = annual_sales * bw
        # split across 12 months with seasonal noise
        month_weights = np.random.dirichlet(np.ones(12) * 6)
        for month, mw in zip(MONTHS, month_weights):
            sales = brand_annual_sales * mw
            month_margin = max(0.05, np.random.normal(margin, 0.025))
            purchase = sales * (1 - month_margin)
            rows.append({
                "Date": month.strftime("%Y-%m-%d"),
                "Vendor": vendor,
                "Brand": brand,
                "Purchase_Amount": round(purchase, 2),
                "Sales_Amount": round(sales, 2),
            })

df = pd.DataFrame(rows)
df = df.sort_values(["Date", "Vendor", "Brand"]).reset_index(drop=True)

df.to_excel("data/vendor_performance_sample_data.xlsx", index=False, sheet_name="Transactions")
df.to_csv("data/vendor_performance_sample_data.csv", index=False)

print(df.shape)
print(df.head(10))
print("\nAnnual totals:")
print("Total Sales ($M):", round(df["Sales_Amount"].sum()/1e6, 2))
print("Total Purchase ($M):", round(df["Purchase_Amount"].sum()/1e6, 2))
print("Gross Profit ($M):", round((df["Sales_Amount"].sum()-df["Purchase_Amount"].sum())/1e6, 2))
print("Profit Margin %:", round((df["Sales_Amount"].sum()-df["Purchase_Amount"].sum())/df["Sales_Amount"].sum()*100, 2))
