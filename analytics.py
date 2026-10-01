"""
Analytics layer: turns raw Transaction rows into the KPIs, rankings and
low-performer scores shown on the dashboard. Kept separate from app.py so
the calculation logic is easy to find, test and explain in a viva.
"""

import pandas as pd
from database import get_session, Transaction

# Rough category tagging for vendors, purely for the "Vendors" table /
# category-level charts (mirrors how the reference platform groups vendors).
VENDOR_CATEGORY = {
    "Diageo North America Inc": "Spirits",
    "Martignetti Companies": "Distributor",
    "Pernod Ricard USA": "Spirits",
    "Jim Beam Brands Company": "Spirits",
    "Bacardi USA Inc": "Spirits",
    "Constellation Brands": "Beer",
    "E & J Gallo Winery": "Wine",
    "Brown-Forman Corp": "Spirits",
    "Ultra Beverage Co": "Beer",
    "M S Walker Inc": "Distributor",
    "Dunn Wine Brokers": "Wine",
    "Circa Wines": "Wine",
    "Park Street Imports LLC": "Distributor",
    "Highland Wine Merchants": "Wine",
    "Alisa Carr Beverages": "Wine",
}


def _load_df():
    session = get_session()
    try:
        rows = session.query(Transaction).all()
        data = [r.to_dict() for r in rows]
    finally:
        session.close()
    if not data:
        return pd.DataFrame(columns=["date", "vendor", "brand", "purchase_amount", "sales_amount"])
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    return df


def kpis():
    df = _load_df()
    if df.empty:
        return {"total_sales": 0, "total_purchase": 0, "gross_profit": 0, "profit_margin": 0,
                "unsold_capital": 0, "active_vendors": 0, "deltas": {}}
    total_sales = df["sales_amount"].sum()
    total_purchase = df["purchase_amount"].sum()
    gross_profit = total_sales - total_purchase
    margin = (gross_profit / total_sales * 100) if total_sales else 0
    # Unsold capital: modelled as purchase value not yet converted to sales this month (approximation)
    unsold_capital = max(0, (total_purchase - total_sales * 0.97)) * 0.15

    deltas = _period_over_period_deltas(df)

    return {
        "total_sales": round(total_sales / 1e6, 2),
        "total_purchase": round(total_purchase / 1e6, 2),
        "gross_profit": round(gross_profit / 1e6, 2),
        "profit_margin": round(margin, 1),
        "unsold_capital": round(unsold_capital / 1e6, 2),
        "active_vendors": df["vendor"].nunique(),
        "deltas": deltas,
    }


def _period_over_period_deltas(df):
    """Compares the most recent half of months against the earlier half,
    so KPI cards can show a real (not fabricated) 'vs prior period' figure."""
    months = sorted(df["date"].dt.to_period("M").unique())
    if len(months) < 2:
        return {}
    mid = len(months) // 2
    earlier_months, recent_months = months[:mid] if mid > 0 else months[:1], months[mid:]
    df_period = df.copy()
    df_period["ym"] = df_period["date"].dt.to_period("M")

    def totals(month_list):
        sub = df_period[df_period["ym"].isin(month_list)]
        s = sub["sales_amount"].sum()
        p = sub["purchase_amount"].sum()
        m = ((s - p) / s * 100) if s else 0
        return s, p, m

    s_prev, p_prev, m_prev = totals(earlier_months)
    s_rec, p_rec, m_rec = totals(recent_months)

    def pct_change(new, old):
        if old == 0:
            return 0.0
        return round((new - old) / old * 100, 1)

    return {
        "total_sales": pct_change(s_rec, s_prev),
        "total_purchase": pct_change(p_rec, p_prev),
        "profit_margin": round(m_rec - m_prev, 1),  # percentage-point change
    }


def top_vendors(n=10):
    df = _load_df()
    if df.empty:
        return []
    g = df.groupby("vendor")["sales_amount"].sum().sort_values(ascending=False).head(n)
    return [{"name": k, "sales": round(v / 1e6, 2)} for k, v in g.items()]


def top_brands(n=10):
    df = _load_df()
    if df.empty:
        return []
    g = df.groupby("brand")["sales_amount"].sum().sort_values(ascending=False).head(n)
    return [{"name": k, "sales": round(v / 1e6, 2)} for k, v in g.items()]


def purchase_contribution(n=10):
    df = _load_df()
    if df.empty:
        return {"vendors": [], "top10_total_pct": 0}
    total_purchase = df["purchase_amount"].sum()
    g = df.groupby("vendor")["purchase_amount"].sum().sort_values(ascending=False)
    top = g.head(n)
    pct = (top / total_purchase * 100).round(1)
    result = [{"name": k, "pct": float(v)} for k, v in pct.items()]
    return {"vendors": result, "top10_total_pct": round(float(pct.sum()), 1)}


def vendor_scores():
    """Weighted performance score per vendor: 0.6*margin + 0.4*sales-volume (both min-max normalised)."""
    df = _load_df()
    if df.empty:
        return pd.DataFrame(columns=["vendor", "sales", "purchase", "margin", "score"])
    g = df.groupby("vendor").agg(sales=("sales_amount", "sum"), purchase=("purchase_amount", "sum")).reset_index()
    g["margin"] = (g["sales"] - g["purchase"]) / g["sales"].replace(0, 1)

    def norm(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5

    g["margin_n"] = norm(g["margin"])
    g["sales_n"] = norm(g["sales"])
    g["score"] = (0.6 * g["margin_n"] + 0.4 * g["sales_n"]).round(3)
    return g.sort_values("score")


def low_vendors(n=5):
    g = vendor_scores()
    if g.empty:
        return []
    low = g.head(n)
    return [{"name": r["vendor"], "score": float(r["score"])} for _, r in low.iterrows()]


def all_vendors_table():
    """Full vendor list for the Vendors page, with rank/score/category."""
    g = vendor_scores().sort_values("score", ascending=False).reset_index(drop=True)
    rows = []
    for i, r in g.iterrows():
        rows.append({
            "rank": i + 1,
            "vendor": r["vendor"],
            "category": VENDOR_CATEGORY.get(r["vendor"], "Other"),
            "sales": round(r["sales"] / 1e6, 2),
            "purchase": round(r["purchase"] / 1e6, 2),
            "margin": round(r["margin"] * 100, 1),
            "score": round(r["score"] * 100, 1),
            "status": "Low Performing" if r["score"] < 0.35 else ("Watch" if r["score"] < 0.55 else "Healthy"),
        })
    return rows


def low_brands_scatter():
    df = _load_df()
    if df.empty:
        return []
    g = df.groupby("brand").agg(sales=("sales_amount", "sum"), purchase=("purchase_amount", "sum")).reset_index()
    g["margin"] = ((g["sales"] - g["purchase"]) / g["sales"].replace(0, 1) * 100).round(1)
    g["sales_scaled"] = (g["sales"] / g["sales"].max() * 1000).round(1) if g["sales"].max() else 0
    out = []
    for _, r in g.iterrows():
        out.append({
            "brand": r["brand"],
            "sales": float(r["sales_scaled"]),
            "margin": float(r["margin"]),
            "low_performing": "Yes" if r["margin"] < 30 else "No",
        })
    return out


def monthly_trend():
    df = _load_df()
    if df.empty:
        return {"months": [], "sales": [], "purchase": [], "margin": []}
    df["month"] = df["date"].dt.strftime("%b %Y")
    order = df[["date", "month"]].drop_duplicates().sort_values("date")["month"].tolist()
    g = df.groupby("month").agg(sales=("sales_amount", "sum"), purchase=("purchase_amount", "sum")).reindex(order)
    margin = ((g["sales"] - g["purchase"]) / g["sales"].replace(0, 1) * 100).round(1)
    return {
        "months": order,
        "sales": [round(v / 1e6, 2) for v in g["sales"]],
        "purchase": [round(v / 1e6, 2) for v in g["purchase"]],
        "margin": [float(v) for v in margin],
    }


def performance_by_category():
    df = _load_df()
    if df.empty:
        return []
    df["category"] = df["vendor"].map(VENDOR_CATEGORY).fillna("Other")
    scores = vendor_scores()
    scores["category"] = scores["vendor"].map(VENDOR_CATEGORY).fillna("Other")
    g = scores.groupby("category")["score"].mean().sort_values(ascending=False)
    return [{"category": k, "score": round(float(v) * 100, 1)} for k, v in g.items()]
