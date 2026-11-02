"""Create a small, deterministic SQLite database for the depot agent.

The data is hand-written (not random) so that eval answers are known in advance.

Run: python -m data.seed
"""
import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "depot.db"

SCHEMA = """
CREATE TABLE warehouses (
    id   TEXT PRIMARY KEY,
    city TEXT NOT NULL
);

CREATE TABLE products (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    category       TEXT NOT NULL,
    brand          TEXT NOT NULL,
    unit           TEXT NOT NULL,
    unit_price_usd REAL NOT NULL
);

CREATE TABLE stock (
    product_id   TEXT NOT NULL REFERENCES products(id),
    warehouse_id TEXT NOT NULL REFERENCES warehouses(id),
    quantity     INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (product_id, warehouse_id)
);

CREATE TABLE substitutes (
    product_id    TEXT NOT NULL REFERENCES products(id),
    substitute_id TEXT NOT NULL REFERENCES products(id),
    note          TEXT,
    PRIMARY KEY (product_id, substitute_id)
);
"""

WAREHOUSES = [
    ("DAL", "Dallas"),
    ("HOU", "Houston"),
    ("ATL", "Atlanta"),
]

PRODUCTS = [
    # id, name, category, brand, unit, unit_price_usd
    ("SHG-001", "Ridgeline Architectural Shingle - Charcoal", "roofing_shingle", "Ridgeline", "bundle", 38.50),
    ("SHG-002", "Ridgeline Architectural Shingle - Weathered Wood", "roofing_shingle", "Ridgeline", "bundle", 38.50),
    ("SHG-003", "Summit Pro Laminate Shingle - Charcoal", "roofing_shingle", "Summit", "bundle", 41.00),
    ("SHG-004", "Valor 3-Tab Shingle - Black", "roofing_shingle", "Valor", "bundle", 29.00),
    ("UND-001", "StormGuard Synthetic Underlayment", "underlayment", "StormGuard", "roll", 92.00),
    ("UND-002", "#30 Felt Underlayment", "underlayment", "Northline", "roll", 24.00),
    ("ICE-001", "IceBlock Ice & Water Shield", "underlayment", "IceBlock", "roll", 118.00),
    ("NAL-001", "Coil Roofing Nails 1-1/4 in", "fastener", "Northline", "box", 64.00),
    ("GUT-001", "5 in K-Style Aluminium Gutter 10 ft - White", "gutter", "Northline", "piece", 14.75),
    ("INS-001", "ThermaBatt R-30 Fiberglass Insulation", "insulation", "ThermaBatt", "bag", 57.00),
]

STOCK = {
    "SHG-001": {"DAL": 120, "HOU": 450, "ATL": 0},
    "SHG-002": {"DAL": 300, "HOU": 80, "ATL": 210},
    "SHG-003": {"DAL": 260, "HOU": 0, "ATL": 95},
    "SHG-004": {"DAL": 900, "HOU": 600, "ATL": 400},
    "UND-001": {"DAL": 40, "HOU": 15, "ATL": 22},
    "UND-002": {"DAL": 200, "HOU": 140, "ATL": 0},
    "ICE-001": {"DAL": 0, "HOU": 30, "ATL": 12},
    "NAL-001": {"DAL": 75, "HOU": 50, "ATL": 60},
    "GUT-001": {"DAL": 500, "HOU": 320, "ATL": 0},
    "INS-001": {"DAL": 0, "HOU": 0, "ATL": 180},
}

SUBSTITUTES = [
    ("SHG-001", "SHG-003", "Same colour (Charcoal), comparable architectural look, higher wind rating with 6 nails"),
    ("SHG-001", "SHG-002", "Same product line, different colour"),
    ("SHG-002", "SHG-001", "Same product line, different colour"),
    ("SHG-003", "SHG-001", "Same colour (Charcoal), comparable architectural look, lower maximum wind rating"),
    ("UND-002", "UND-001", "Synthetic upgrade: lighter and covers 10 squares per roll"),
]


def seed(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO warehouses VALUES (?, ?)", WAREHOUSES)
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)", PRODUCTS)
        conn.executemany(
            "INSERT INTO stock VALUES (?, ?, ?)",
            [(pid, wid, qty) for pid, by_wh in STOCK.items() for wid, qty in by_wh.items()],
        )
        conn.executemany("INSERT INTO substitutes VALUES (?, ?, ?)", SUBSTITUTES)
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    path = seed(os.environ.get("DEPOT_DB_PATH", DEFAULT_DB_PATH))
    print(f"Seeded {path}")
