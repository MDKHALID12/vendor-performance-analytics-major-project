# Vendor Performance Data Analytics — Advanced Web Application

A multi-page, database-backed vendor analytics platform built for the major
project. This is the **advanced version**: it replaces the single-page demo
with a full sidebar-navigation app (Overview, Vendors, Performance, Low
Performers, Upload Data, Reports) backed by a real SQLite database, and
supports uploading your own CSV/Excel dataset to recompute everything live.

## What's new vs. the earlier single-page version

- **Real database** (SQLite via SQLAlchemy) instead of in-memory Python lists.
- **CSV/Excel upload** — replace or append a new dataset and the entire
  dashboard (KPIs, rankings, low-performer scores, trend charts) recomputes
  from the database automatically.
- **Multi-page app** with sidebar navigation, matching a professional BI
  product layout (Overview / Vendors / Performance / Low Performers /
  Upload / Reports).
- **Real "vs prior period" deltas** on the KPI cards — computed by
  comparing the first half vs second half of the months in your dataset
  (not fabricated numbers).
- **Searchable/filterable Vendors table** with rank, category, score and
  status badges (Healthy / Watch / Low Performing).
- **CSV report exports** (Vendor Performance, Low Performing Vendors, Raw
  Transactions).

## Tech Stack

| Layer     | Technology                                         |
|-----------|------------------------------------------------------|
| Backend   | Python 3, Flask (multi-page routes + REST API)       |
| Database  | SQLite, accessed via SQLAlchemy ORM                   |
| Frontend  | HTML5, CSS3, vanilla JavaScript                       |
| Charts    | Chart.js (bundled locally, no internet needed)        |
| Data prep | pandas + openpyxl (reads uploaded CSV/Excel files)    |

## Project Structure

```
vendor_dashboard/
├── app.py                 # Flask app: page routes, upload handling, REST API
├── database.py             # SQLAlchemy engine, Transaction model, seeding
├── analytics.py             # KPI / ranking / scoring calculations
├── generate_sample_data.py  # Script that generated the bundled sample dataset
├── requirements.txt
├── data/
│   ├── vendor_performance_sample_data.xlsx   # Bundled 12-month sample dataset
│   └── vendor_performance_sample_data.csv
├── instance/
│   └── vendor_performance.db   # SQLite database file (created on first run)
├── templates/
│   ├── base.html            # Shared sidebar layout
│   ├── overview.html
│   ├── vendors.html
│   ├── performance.html
│   ├── low_performers.html
│   ├── upload.html
│   └── reports.html
└── static/
    ├── css/style.css
    └── js/ (common.js, overview.js, vendors.js, performance.js, low_performers.js, vendor/chart.umd.js)
```

## How to Run

```
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000/** in your browser.

On first run, the SQLite database (`instance/vendor_performance.db`) is
automatically created and seeded from the bundled sample dataset
(`data/vendor_performance_sample_data.xlsx`) — 12 months (Sep 2025–Aug 2026)
of vendor/brand purchase and sales data for 15 vendors, matching the vendors
and figures from the original Power BI dashboard (Diageo, Bacardi, Pernod
Ricard, Jim Beam, and the 5 flagged low-performing vendors).

## How the Upload feature works

Go to **Upload Data** in the sidebar:

1. Choose a CSV or Excel file with these exact columns:
   `Date, Vendor, Brand, Purchase_Amount, Sales_Amount`
   (Date format: `YYYY-MM-DD`; each row = one vendor+brand's totals for one month.)
2. Choose **Replace** (wipes existing data) or **Append** (adds to existing data).
3. Click **Upload & Recompute Dashboard** — you'll be redirected to the
   Overview page with the new totals, rankings and charts.
4. **Reset to Sample Dataset** restores the original bundled data at any time.

You can download the bundled sample file itself from the **Reports** page
(Excel or CSV), edit a few numbers, and re-upload it to see the dashboard
change live — a good thing to demo in your viva.

## KPI / Scoring logic (for your viva)

- **Gross Profit** = Total Sales − Total Purchase
- **Profit Margin %** = Gross Profit / Total Sales × 100
- **Vendor Performance Score** = 0.6 × (normalized profit margin) + 0.4 ×
  (normalized sales volume), both min-max scaled 0–1 across all vendors in
  the current dataset. Lowest-scoring vendors are flagged "Low Performing".
- **Low Performing Brand** = average profit margin across that brand's
  transactions is below 30%.
- **"vs prior period" KPI deltas** = the dataset's months are split into an
  earlier half and a recent half; the delta is the % change (or
  percentage-point change for margin) between the two halves.

## Extending this further

- Swap the SQLite URL in `database.py` for a MySQL/Postgres connection
  string to move to a production database.
- Add Flask-Login for Admin/Viewer roles (Admin can upload, Viewer is
  read-only).
- Add a scheduled job (APScheduler) to auto-refresh from a live data source.
- Add PDF export (the `pdf` skill / a library like `reportlab`) alongside
  the existing CSV export.
