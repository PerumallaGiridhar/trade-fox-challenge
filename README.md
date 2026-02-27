## Portfolio & PnL Tracker (FastAPI)

A lightweight FastAPI backend that tracks trades, maintains portfolio positions, and computes realized and unrealized profit & loss (PnL) using **FIFO accounting**.

The service is intentionally **stateless and in-memory**, focused on correctness and clarity rather than persistence or scaling concerns.

---

## Tech Stack

- **Language**: Python (3.13, as used in Docker image)
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Data models**: `dataclasses` + Pydantic
- **Testing**: `pytest` + `fastapi.testclient`
- **Dependency / runtime tool**: `uv` (via `pyproject.toml` + `uv.lock`)

---

## Project Structure

```text
.
├── main.py                # FastAPI app + router wiring + health endpoint
├── app
│   ├── engine.py          # In‑memory portfolio engine and FIFO PnL logic
│   ├── models.py          # Pydantic request models
│   ├── routes.py          # API routes using a shared PortfolioEngine instance
│   └── prices.py          # Hardcoded latest prices used for unrealized PnL
├── tests
│   ├── conftest.py        # Test client + engine reset fixture
│   └── test_portfolio.py  # End‑to‑end tests for trades, portfolio, PnL
├── pyproject.toml         # Dependencies (FastAPI, Uvicorn, pytest, etc.)
├── uv.lock                # Resolved lockfile for `uv`
└── Dockerfile             # Production image using `uv` + Uvicorn
```

---

## Running the Service

You can run the API either **with Docker** (recommended for a quick spin‑up) or **directly with `uv`**.

### 1. With Docker (recommended)

Build the image:

```bash
cd trade-fox-challenge
docker build -t trade-api .
```

Start the server:

```bash
docker run -it --rm --name trade-api -p 9005:9005 trade-api:latest
```

Open Swagger UI:

```text
http://127.0.0.1:9005/docs
```

Health / readiness endpoint:

```text
GET /ready  -> { "status": "running" }
```

### 2. Locally with `uv` (no Docker)

Prerequisites:

- Python 3.13 installed
- [`uv`](https://github.com/astral-sh/uv) available on your PATH

Install dependencies:

```bash
cd trade-fox-challenge
uv sync
```

Run the API locally:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 9005
```

Then open:

```text
http://127.0.0.1:9005/docs
```


## Quick Test (Using curl)

### 1️⃣ Add Buy Trades

```bash
curl -X POST "http://127.0.0.1:9005/trades" \
  -H "Content-Type: application/json" \
  -d '{
        "symbol": "BTC",
        "side": "buy",
        "price": 40000,
        "quantity": 1
      }'
```

```bash
curl -X POST "http://127.0.0.1:9005/trades" \
  -H "Content-Type: application/json" \
  -d '{
        "symbol": "BTC",
        "side": "buy",
        "price": 42000,
        "quantity": 1
      }'
```

---

### 2️⃣ Add Sell Trade (FIFO enforced automatically)

```bash
curl -X POST "http://127.0.0.1:9005/trades" \
  -H "Content-Type: application/json" \
  -d '{
        "symbol": "BTC",
        "side": "sell",
        "price": 43000,
        "quantity": 1.5
      }'
```

---

### 3️⃣ Check Portfolio

```bash
curl "http://127.0.0.1:9005/portfolio"
```

Expected output:

```json
{
  "BTC": {
    "quantity": 0.5,
    "average_entry_price": 42000.0
  }
}
```

---

### 4️⃣ Check PnL

```bash
curl "http://127.0.0.1:9005/pnl"
```

Example output:

```json
{
  "realized_pnl": 3500.0,
  "unrealized_pnl": 1000.0
}
```

*(Unrealized PnL depends on the hardcoded latest price defined in `prices.py`.)*

---

## Features

- **Trade capture**: Add `buy` and `sell` trades per symbol
- **FIFO accounting**: Sells are matched against the **oldest open buys**
- **Portfolio view**: Quantity and average entry price per symbol
- **PnL reporting**:
  - Realized PnL from closed positions
  - Unrealized PnL from remaining open quantities using latest prices
- **In-memory engine**: Single-process, single-user, non-persistent
- **Test coverage**: Edge cases around FIFO behavior and validation

---

## Accounting Method

This implementation uses **FIFO (First-In-First-Out)** accounting on a per-symbol basis.

- Each **buy trade** is recorded as a standalone transaction.
- Each **sell trade** is internally expanded into one or more sell records that:
  - Reference specific buy trade IDs via a `reference_id` field.
  - Consume quantity starting from the **oldest** open buy (FIFO).
- Remaining quantity on each buy is computed by subtracting all linked sells.
- No derived state (positions or PnL aggregates) is stored; it is **recomputed on demand** from the trade list.

This design keeps PnL **deterministic, auditable, and easy to reason about**.

---

## API Endpoints

### `POST /trades`

Add a trade.

Request body (Pydantic model: `TradeRequest`):

```json
{
  "symbol": "BTC",
  "side": "buy",
  "price": 40000,
  "quantity": 1
}
```

- **side**: `"buy"` or `"sell"` (anything else is rejected with `400` / `422`).
- **Sell behavior**:
  - Matches against the oldest open buys (FIFO).
  - If the requested sell quantity is greater than the available position, returns **HTTP 400** with `"Not enough quantity to sell"`.
  - Selling without any holdings also returns **HTTP 400**.

Successful response:

```json
{ "status": "ok" }
```

### `GET /portfolio`

Returns the current open positions per symbol:

```json
{
  "BTC": {
    "quantity": 1.5,
    "average_entry_price": 41333.33
  }
}
```

- **quantity**: Total remaining open quantity after consumes from sells.
- **average_entry_price**: Weighted average price of the remaining open buys.
- If there are no open positions, returns an empty object: `{}`.

### `GET /pnl`

Returns portfolio PnL:

```json
{
  "realized_pnl": 3500.0,
  "unrealized_pnl": 2000.0
}
```

- **Realized PnL**:
  - Sum over all sells: \((sell\_price - buy\_price) * matched\_quantity\).
  - Uses the `reference_id` linkage to the original buy trades.
- **Unrealized PnL**:
  - Computed only on remaining open quantities.
  - Uses latest prices from `app/prices.py`:

    ```python
    LATEST_PRICES = {
        "BTC": 40000,
        "ETH": 2000,
    }
    ```

  - Symbols not present in `LATEST_PRICES` are effectively priced at `0` for unrealized PnL.

### `GET /ready`

Simple liveness / readiness check provided by `main.py`:

```json
{ "status": "running" }
```

### Error Handling

- Unexpected server errors are caught by a generic exception handler and surfaced as:

  ```json
  { "detail": "Internal Server Error" }
  ```

- FastAPI / Pydantic validation errors (missing fields, wrong types, invalid enum values) are returned as standard **422** responses.

---

## Example FIFO Flow

1. Buy 1 BTC @ 40,000  
2. Buy 1 BTC @ 42,000  
3. Sell 1.5 BTC @ 43,000  

FIFO behavior:

- 1.0 BTC sold from the 40,000 buy
- 0.5 BTC sold from the 42,000 buy

Realized PnL:

```text
(43000 - 40000) * 1.0
+ (43000 - 42000) * 0.5
= 3500
```

Remaining position:

```text
0.5 BTC @ 42000
```

---

## Running Tests

### Inside Docker

With the container image already built:

```bash
docker run -it --rm --name trade-api-test trade-api:latest uv run pytest -s -v tests/
```

### Locally with `uv`

From the project root:

```bash
uv run pytest -s -v tests/
```

The tests cover:

- Multiple buys and weighted average pricing
- FIFO sell behavior across one or many buy lots
- Partial sells that span multiple buys
- Full position closure (portfolio becomes `{}`)
- Multiple symbols with independent positions
- Selling **more than holdings** (returns HTTP 400)
- Selling without any holdings (returns HTTP 400)
- Input validation for invalid `side` and missing fields

---

## Assumptions & Limitations

- **Single user / session**:
  - All trades are stored in a single in-memory `PortfolioEngine` instance.
- **In-memory only**:
  - No database or persistence layer; state is lost on process restart.
- **No authentication / authorization**.
- **No concurrency guarantees**:
  - Not designed for high-concurrency workloads or multiple workers.
- **Hardcoded prices**:
  - Latest prices live in `app/prices.py` and must be updated in code.

---

## Summary

This implementation prioritizes:

- **Correct FIFO trade matching**
- **Deterministic PnL calculation**
- **Auditability of trade → PnL linkage**
- **Simple, maintainable architecture**

It is intentionally minimal but provides a solid foundation for a more full-featured portfolio and PnL service.