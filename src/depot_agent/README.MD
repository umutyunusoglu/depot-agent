# Depot Agent

A small LLM agent that answers questions from the sales team of a fictional roofing materials distributor (Northline Building Supply). It combines structured data (stock, prices, substitutes in SQLite) with RAG over product spec sheets and company policies. Everything runs locally with Ollama.

I built it in one evening as a learning project, to understand how agents, tool calling and RAG work by writing them from scratch, without a framework. All data is made up.

## Example

```
$ python agent.py "What is the fire rating of the Valor 3-tab shingle?"
  -> search_product_docs({'product_name': 'Valor 3-tab shingle', 'question': 'fire rating'})
  ...
The technical documentation for Valor 3-tab shingle (SHG-004 Black) includes wind rating,
minimum roof slope and minimum installation temperature, but it does not specify a fire rating.
```

The Valor spec sheet deliberately has no fire rating, while two other shingles are rated "Class A". The agent correctly says it doesn't know instead of borrowing another product's value.

## How it works

The agent loop (`agent.py`) sends the question to the model with four tools. The model either answers or asks for a tool call; the loop runs the tool, sends the result back and repeats, up to a step limit.

| Tool | What it does |
|---|---|
| `get_product_info` | Price, unit and stock in every warehouse (SQLite) |
| `get_substitutes` | Approved substitutes, with their stock |
| `search_product_docs` | RAG over one product's spec sheet |
| `search_policies` | RAG over returns, delivery and pickup policies |

## Design decisions

- **Typed tools instead of letting the model write SQL.** Safer and easier to test. All user input goes into parameterised queries.
- **Tools take product names, not ids.** Users talk about "Summit Pro", not "SHG-003". If a name matches several products, the tool returns the candidates so the model can ask the user.
- **Errors are returned as data, not raised.** An unknown tool, bad arguments or a failing tool becomes `{"error": ...}`, so the model can recover and the loop never crashes.
- **No vector database.** With 30 chunks, embeddings are kept in memory and ranked by cosine similarity. At larger scale I'd use something like pgvector.
- **Chunks are document sections with the title prepended**, so a chunk like "Wind rating: 130 mph" still says which product it belongs to.
- **Spec search is filtered to the requested product.** Without the filter, "Valor fire rating" retrieves other shingles' "Class A" lines.

## What I measured

Single run per question on my laptop (`granite4.2:8b`), so the numbers are indicative only.

| Question | Correct | Steps | Time | Input tokens |
|---|---|---|---|---|
| Summit Pro wind rating | Yes | 2 | 6.7 s | 1,614 |
| Return policy for unopened shingles | Yes | 2 | 6.0 s | 1,551 |
| Valor fire rating (not in docs) | Yes, said it didn't know | 4 | 28.4 s | 3,882 |
| Aluminium gutter warranty (no spec sheet) | Yes, said it didn't know | 4 | 24.6 s | 3,390 |

When the answer wasn't in the docs, the agent used about twice the steps and tokens, because it kept searching before admitting it didn't know. Input tokens grow with every step since the whole conversation is resent. In the Valor case it repeated an identical search. Adding the matched product to the tool result and an instruction to the prompt did not change this.

## Limitations and next steps

- Block repeated identical tool calls in the loop itself, rather than relying on the prompt, and measure the effect.
- Turn the questions above into an automated eval set (expected facts, expected tools, "I don't know" cases) and run it several times per change, since model output varies between runs.
- Add unit tests for the tools.
- Product name matching is simple word matching, and the product filter checks ids in chunk text, so a doc section without an id (e.g. "Choosing between them" in the underlayment doc) is never retrieved. Metadata on each chunk would be cleaner.

## Run it

Requires Python 3.10+ and [Ollama](https://ollama.com).

```bash
ollama pull granite4.2:8b
ollama pull nomic-embed-text
pip install ollama

python data/seed.py   # creates data/depot.db
python agent.py "Do we have 200 bundles of SHG-001 in Dallas? If not, suggest a substitute."
```
