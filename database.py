"""
Database layer for Vendor Performance Data Analytics.

Uses SQLAlchemy ORM with SQLite (file-based, zero-config) so the project
demonstrates real database-backed data persistence instead of in-memory
Python lists. Swapping SQLITE_URL for a MySQL/Postgres URL is a one-line
change if a production database is preferred later.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "vendor_performance.db")
SQLITE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(SQLITE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class Transaction(Base):
    """One row = one vendor+brand's purchase/sales figures for a given month."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    vendor = Column(String(120), nullable=False)
    brand = Column(String(120), nullable=False)
    purchase_amount = Column(Float, nullable=False)
    sales_amount = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "vendor": self.vendor,
            "brand": self.brand,
            "purchase_amount": self.purchase_amount,
            "sales_amount": self.sales_amount,
        }


def init_db():
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()


def seed_from_dataframe(df, replace=True):
    """Load a pandas DataFrame with columns
    [Date, Vendor, Brand, Purchase_Amount, Sales_Amount] into the database."""
    session = get_session()
    try:
        if replace:
            session.query(Transaction).delete()
        for _, row in df.iterrows():
            txn = Transaction(
                date=_parse_date(row["Date"]),
                vendor=str(row["Vendor"]).strip(),
                brand=str(row["Brand"]).strip(),
                purchase_amount=float(row["Purchase_Amount"]),
                sales_amount=float(row["Sales_Amount"]),
            )
            session.add(txn)
        session.commit()
        count = session.query(Transaction).count()
        return count
    finally:
        session.close()


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "date"):
        try:
            return value.date()
        except Exception:
            pass
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def row_count():
    session = get_session()
    try:
        return session.query(Transaction).count()
    finally:
        session.close()
