from asyncio import Condition
import sqlite3

DB_PATH = "./data/depot.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _find_products(conn, text: str):
    words = [w[:-1] if w.endswith("s") > 3 else w for w in text.lower().split()]

    if not words:
        return []

    conditions = " AND ".join("LOWER(name) LIKE ?" for _ in words)
    params = [f"%{w}%" for w in words]
    sql = f"SELECT * FROM products WHERE ({conditions}) OR UPPER(id) = ?"
    return conn.execute(sql, params + [text.strip().upper()]).fetchall()


def get_product_info(product_name: str) -> dict:

    conn = _connect()

    try:
        matches = _find_products(conn, product_name)
        if not matches:
            return {"error": f"No product matches '{product_name}'."}
        if len(matches) > 1:
            return {
                "error": "Ambiguous product name. Ask the user which one they mean.",
                "candidates": [m["name"] for m in matches],
            }
        p = matches[0]
        rows = conn.execute(
            """SELECT w.city, s.quantity
               FROM stock s JOIN warehouses w ON w.id = s.warehouse_id
               WHERE s.product_id = ?""",
            (p["id"],),
        ).fetchall()
        return {
            "id": p["id"],
            "name": p["name"],
            "unit": p["unit"],
            "price_usd": p["unit_price_usd"],
            "stock": {r["city"]: r["quantity"] for r in rows},
        }
    finally:
        conn.close()


def get_substitutes(product_name):

    conn = _connect()

    try:
        matches = _find_products(conn, product_name)
        if not matches:
            return {"error": f"No product matches '{product_name}'."}
        if len(matches) > 1:

            return {
                "error": "Ambiguous product name. Ask the user which one they mean.",
                "candidates": [m["name"] for m in matches],
            }
        p = matches[0]
        rows = conn.execute(
            """
              SELECT sub.substitute_id, sub.note
              FROM substitutes sub
              JOIN products p ON p.id = sub.substitute_id
              WHERE sub.product_id = ?
              """,
            (p["id"],),
        ).fetchall()

        substitues = []
        for row in rows:
            info = get_product_info(row["substitute_id"])
            info["note"] = row["note"]
            substitues.append(info)

        return {"product": p["name"], "substitues": substitues}
    finally:
        conn.close()
