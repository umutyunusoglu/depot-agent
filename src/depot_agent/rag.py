import math
from pathlib import Path

from ollama import embed

from tools import _connect, _find_products

EMBED_MODEL = "nomic-embed-text"
DOCS_DIR = Path("data/docs")  # DÜZELTME: string değil Path olmalı, .glob için
_INDEX = None  # ilk aramada bir kez oluşturulur


def _chunk(path: Path) -> list[dict]:
    """Her '## ' bölümü bir parça. Başlık her parçanın başına eklenir."""
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].lstrip("# ").strip()
    sections, current = [], []
    for line in lines[1:]:
        if line.startswith("## ") and current:
            sections.append(current)
            current = []
        current.append(line)  # DÜZELTME: eksikti, hiç parça üretilmiyordu
    if current:
        sections.append(current)

    chunks = []
    for section in sections:
        body = "\n".join(section).strip()
        if body:
            chunks.append({"source": path.name, "text": f"{title}\n{body}"})
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def _get_index() -> list[dict]:
    global _INDEX
    if _INDEX is None:
        chunks = [c for p in sorted(DOCS_DIR.glob("*.md")) for c in _chunk(p)]
        # DÜZELTME: .embeddings eksikti
        vectors = embed(model=EMBED_MODEL, input=[c["text"] for c in chunks]).embeddings
        for chunk, vector in zip(chunks, vectors):
            chunk["vector"] = vector
        _INDEX = chunks
    return _INDEX


def _search(question: str, chunks: list[dict], k: int = 3) -> list[dict]:
    q = embed(model=EMBED_MODEL, input=question).embeddings[0]
    ranked = sorted(chunks, key=lambda c: _cosine(q, c["vector"]), reverse=True)
    return [{"source": c["source"], "text": c["text"]} for c in ranked[:k]]


def search_policies(question: str) -> dict:
    """Search company policies: returns, delivery, pickup and pricing rules.

    Args:
        question: What the user wants to know, e.g. 'return policy for unopened items'.
    """
    chunks = [c for c in _get_index() if c["source"] == "policies.md"]
    return {"results": _search(question, chunks)}


def search_product_docs(product_name: str, question: str) -> dict:
    """Search the technical spec sheet of a specific product: coverage, wind and fire
    rating, installation temperature, roof slope, warranty.

    Args:
        product_name: The product name or part of it (e.g. 'Summit Pro'), or its id.
        question: What the user wants to know, e.g. 'minimum installation temperature'.
    """
    conn = _connect()
    try:
        products = _find_products(conn, product_name)  # DÜZELTME: argüman sırası
    finally:
        conn.close()  # DÜZELTME: bağlantı kapatılmıyordu
    if not products:
        return {"error": f"No product matches '{product_name}'."}

    ids = [p["id"] for p in products]
    # DÜZELTME: .contain() yok; ID'lerden herhangi biri metinde geçiyor mu?
    chunks = [c for c in _get_index() if any(pid in c["text"] for pid in ids)]
    matched = [p["name"] for p in products]
    if not chunks:
        return {
            "matched_products": matched,
            "results": [],
            "note": "No spec sheet available for this product.",
        }
    return {"matched_products": matched, "results": _search(question, chunks)}
