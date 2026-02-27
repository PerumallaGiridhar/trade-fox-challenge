# Portfolio & PnL Tracker

A lightweight backend service that tracks trades, calculates portfolio positions, and computes realized and unrealized profit & loss (PnL).

---

## Running Locally

Docker build:

```bash
cd trade-fox-challenge
docker build -t trade-api .
```

Start the server:

```bash
docker run -it --rm --name trade-api -p 9005:9005 trade-api:latest
```

Open Swagger UI:

```
http://127.0.0.1:9005/docs
```

---


## Features

- Add trades (buy/sell)
- FIFO accounting enforced internally
- Portfolio summary per symbol
- Realized PnL
- Unrealized PnL (based on hardcoded latest prices)
- In-memory storage (single user)
- Unit tests covering edge cases

---

## Accounting Method

This implementation uses **FIFO (First-In-First-Out)** accounting.

- Each **buy trade** is recorded as a trade transaction.
- When a sell is executed, the engine automatically links it to the oldest open buy-trades.
- If a sell spans multiple buys, the engine internally splits it into multiple sell transactions referencing those buy-trade IDs.
- Sell-to-buy linkage is stored explicitly for traceability.
- No derived financial state (like stored positions or PnL totals) is permanently stored.

This ensures deterministic and correct realized and unrealized PnL.

---

## API Endpoints

### POST /trades

Add a trade.

Request body:

```json
{
  "symbol": "BTC",
  "side": "buy",
  "price": 40000,
  "quantity": 1
}
```

- `side` must be `"buy"` or `"sell"`.
- Sell orders automatically match the oldest open buy trades (FIFO).

---

### GET /portfolio

Returns current holdings per symbol:

```json
{
  "BTC": {
    "quantity": 1.5,
    "average_entry_price": 41333.33
  }
}
```

- `quantity` = total remaining open quantity
- `average_entry_price` = weighted average of remaining buy trades

---

### GET /pnl

Returns:

```json
{
  "realized_pnl": 3500,
  "unrealized_pnl": 2000
}
```

- **Realized PnL**: profit/loss from closed trades
- **Unrealized PnL**: profit/loss from remaining open quantities using hardcoded latest prices

Latest prices are defined in `prices.py`.

---

## Example Flow

1. Buy 1 BTC @ 40,000  
2. Buy 1 BTC @ 42,000  
3. Sell 1.5 BTC @ 43,000  

FIFO behavior:

- 1 BTC sold from the 40,000 buy
- 0.5 BTC sold from the 42,000 buy

Realized PnL:

```
(43000 - 40000)*1
+ (43000 - 42000)*0.5
= 3500
```

Remaining position:

```
0.5 BTC @ 42000
```

---


## Running Tests

```bash
docker run -it --rm --name trade-api trade-api:latest uv run pytest -s -v tests/
```

Tests cover:

- Multiple buys
- FIFO sell behavior
- Partial sell across multiple buys
- Full position closure
- Multiple symbols
- Selling more than holdings
- PnL correctness

---

## Assumptions

- Single user system
- In-memory storage only
- No authentication
- No persistence across restarts
- Hardcoded latest prices
- No concurrency handling

---

## Summary

This implementation prioritizes:

- Correct FIFO trade matching
- Deterministic PnL calculation
- Clear separation of concerns
- Simple and maintainable design

The focus is correctness and clarity rather than over-engineering.