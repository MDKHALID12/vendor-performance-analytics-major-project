"""
Vendor Performance Data Analytics - Flask Backend (Advanced / Major Project)
-----------------------------------------------------------------------------
Multi-page web application:
  /            Overview dashboard (KPIs, trend, top vendors/brands)
  /vendors     Full vendor table (rank, score, category, status)
  /performance Deeper analytics: trend + performance by category
  /low-performers   Low performing vendors & brands
  /upload      Upload a new CSV/Excel dataset (replaces or appends data)
  /reports     Export CSV reports

Data is stored in a SQLite database (via SQLAlchemy) instead of in-memory
Python lists, and is seeded from a bundled sample dataset
(data/vendor_performance_sample_data.xlsx) on first run.
"""

import os
import io
import pandas as pd
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file

import database as db
import analytics as an

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_FILE = os.path.join(BASE_DIR, "data", "vendor_performance_sample_data.xlsx")

app = Flask(__name__)
app.secret_key = "dev-secret-key-for-flash-messages"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

REQUIRED_COLUMNS = {"Date", "Vendor", "Brand", "Purchase_Amount", "Sales_Amount"}


def ensure_seeded():
    db.init_db()
    if db.row_count() == 0 and os.path.exists(SAMPLE_FILE):
        df = pd.read_excel(SAMPLE_FILE)
        db.seed_from_dataframe(df, replace=True)


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------

@app.route("/")
def overview():
    return render_template("overview.html", active="overview")


@app.route("/vendors")
def vendors():
    return render_template("vendors.html", active="vendors")


@app.route("/performance")
def performance():
    return render_template("performance.html", active="performance")


@app.route("/low-performers")
def low_performers():
    return render_template("low_performers.html", active="low_performers")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("datafile")
        mode = request.form.get("mode", "replace")  # replace | append
        if not file or file.filename == "":
            flash("Please choose a CSV or Excel file to upload.", "error")
            return redirect(url_for("upload"))
        try:
            if file.filename.lower().endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            flash(f"Could not read the file: {e}", "error")
            return redirect(url_for("upload"))

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            flash(f"Missing required column(s): {', '.join(sorted(missing))}. "
                  f"Required columns are: {', '.join(sorted(REQUIRED_COLUMNS))}.", "error")
            return redirect(url_for("upload"))

        count = db.seed_from_dataframe(df, replace=(mode == "replace"))
        flash(f"Upload successful — database now has {count} transaction rows.", "success")
        return redirect(url_for("overview"))

    return render_template("upload.html", active="upload", required_columns=sorted(REQUIRED_COLUMNS))


@app.route("/upload/reset", methods=["POST"])
def upload_reset():
    if os.path.exists(SAMPLE_FILE):
        df = pd.read_excel(SAMPLE_FILE)
        count = db.seed_from_dataframe(df, replace=True)
        flash(f"Reset to sample dataset — {count} rows loaded.", "success")
    return redirect(url_for("upload"))


@app.route("/reports")
def reports():
    return render_template("reports.html", active="reports")


@app.route("/data/sample.xlsx")
def sample_xlsx():
    return send_file(SAMPLE_FILE, as_attachment=True, download_name="vendor_performance_sample_data.xlsx")


@app.route("/data/sample.csv")
def sample_csv():
    csv_path = os.path.join(BASE_DIR, "data", "vendor_performance_sample_data.csv")
    return send_file(csv_path, as_attachment=True, download_name="vendor_performance_sample_data.csv")


@app.route("/reports/export/<kind>")
def export_report(kind):
    if kind == "vendors":
        rows = an.all_vendors_table()
        df = pd.DataFrame(rows)
    elif kind == "transactions":
        session = db.get_session()
        try:
            data = [t.to_dict() for t in session.query(db.Transaction).all()]
        finally:
            session.close()
        df = pd.DataFrame(data)
    elif kind == "low-vendors":
        df = pd.DataFrame(an.low_vendors(n=50))
    else:
        return "Unknown report", 404

    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=f"{kind}_report.csv")


# ---------------------------------------------------------------------
# JSON API (consumed by the frontend charts on every page)
# ---------------------------------------------------------------------

@app.route("/api/kpis")
def api_kpis():
    return jsonify(an.kpis())


@app.route("/api/top-vendors")
def api_top_vendors():
    return jsonify(an.top_vendors())


@app.route("/api/top-brands")
def api_top_brands():
    return jsonify(an.top_brands())


@app.route("/api/purchase-contribution")
def api_purchase_contribution():
    return jsonify(an.purchase_contribution())


@app.route("/api/low-vendors")
def api_low_vendors():
    return jsonify(an.low_vendors())


@app.route("/api/low-brands-scatter")
def api_scatter():
    return jsonify(an.low_brands_scatter())


@app.route("/api/vendors-table")
def api_vendors_table():
    return jsonify(an.all_vendors_table())


@app.route("/api/monthly-trend")
def api_monthly_trend():
    return jsonify(an.monthly_trend())


@app.route("/api/performance-by-category")
def api_perf_category():
    return jsonify(an.performance_by_category())


@app.route("/api/dataset-info")
def api_dataset_info():
    return jsonify({"row_count": db.row_count()})


ensure_seeded()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
