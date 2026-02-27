def post_trade(client, symbol: str, side: str, price: float, quantity: float):
    return client.post(
        "/trades",
        json={
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
        },
    )


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_empty_portfolio(client):
    r = client.get("/portfolio")
    assert r.status_code == 200
    assert r.json() == {}


def test_empty_pnl(client):
    r = client.get("/pnl")
    assert r.status_code == 200
    body = r.json()
    assert "realized_pnl" in body
    assert "unrealized_pnl" in body
    assert approx(body["realized_pnl"], 0.0)
    assert approx(body["unrealized_pnl"], 0.0)


def test_single_buy_portfolio_avg_entry(client):
    r = post_trade(client, "BTC", "buy", 40000, 1)
    assert r.status_code == 200

    r = client.get("/portfolio")
    assert r.status_code == 200
    p = r.json()

    assert "BTC" in p
    assert approx(p["BTC"]["quantity"], 1.0)
    assert approx(p["BTC"]["average_entry_price"], 40000.0)


def test_multiple_buys_weighted_average(client):
    post_trade(client, "BTC", "buy", 40000, 1)
    post_trade(client, "BTC", "buy", 42000, 1)

    r = client.get("/portfolio")
    assert r.status_code == 200
    p = r.json()["BTC"]

    assert approx(p["quantity"], 2.0)
    # weighted avg: (1*40000 + 1*42000)/2 = 41000
    assert approx(p["average_entry_price"], 41000.0)


def test_fifo_sell_consumes_oldest_lot_and_updates_portfolio(client):
    post_trade(client, "BTC", "buy", 40000, 1)
    post_trade(client, "BTC", "buy", 42000, 1)
    post_trade(client, "BTC", "sell", 43000, 1)

    # Portfolio should have 1 BTC left, and it should be the 42000 lot remaining (FIFO)
    r = client.get("/portfolio")
    assert r.status_code == 200
    p = r.json()["BTC"]

    assert approx(p["quantity"], 1.0)
    assert approx(p["average_entry_price"], 42000.0)

    # PnL: realized = (43000 - 40000)*1 = 3000
    # unrealized depends on your hardcoded LATEST_PRICES
    r = client.get("/pnl")
    assert r.status_code == 200
    pnl = r.json()

    assert approx(pnl["realized_pnl"], 3000.0)


def test_sell_split_across_multiple_buys_fifo(client):
    post_trade(client, "BTC", "buy", 40000, 1)
    post_trade(client, "BTC", "buy", 42000, 1)
    post_trade(client, "BTC", "sell", 43000, 1.5)

    # Remaining should be 0.5 BTC from the 42000 lot
    r = client.get("/portfolio")
    assert r.status_code == 200
    p = r.json()["BTC"]
    assert approx(p["quantity"], 0.5)
    assert approx(p["average_entry_price"], 42000.0)

    # Realized:
    # 1.0 from first lot: (43000-40000)*1 = 3000
    # 0.5 from second lot: (43000-42000)*0.5 = 500
    # total = 3500
    r = client.get("/pnl")
    assert r.status_code == 200
    pnl = r.json()
    assert approx(pnl["realized_pnl"], 3500.0)


def test_sell_exactly_all_position_portfolio_empty(client):
    post_trade(client, "BTC", "buy", 40000, 1)
    post_trade(client, "BTC", "sell", 41000, 1)

    r = client.get("/portfolio")
    assert r.status_code == 200
    assert r.json() == {}


def test_multiple_symbols_independent_positions(client):
    post_trade(client, "BTC", "buy", 40000, 1)
    post_trade(client, "ETH", "buy", 2000, 3)
    post_trade(client, "BTC", "buy", 42000, 1)

    r = client.get("/portfolio")
    assert r.status_code == 200
    p = r.json()

    assert "BTC" in p and "ETH" in p
    assert approx(p["BTC"]["quantity"], 2.0)
    assert approx(p["BTC"]["average_entry_price"], 41000.0)

    assert approx(p["ETH"]["quantity"], 3.0)
    assert approx(p["ETH"]["average_entry_price"], 2000.0)


def test_sell_more_than_holdings_returns_400(client):
    post_trade(client, "BTC", "buy", 40000, 1)

    r = post_trade(client, "BTC", "sell", 41000, 2)
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body
    assert "Not enough" in body["detail"]


def test_sell_without_any_holdings_returns_400(client):
    r = post_trade(client, "BTC", "sell", 41000, 1)
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body


def test_invalid_side_rejected(client):
    r = client.post(
        "/trades",
        json={"symbol": "BTC", "side": "hold", "price": 40000, "quantity": 1},
    )
    assert r.status_code in (400, 422)


def test_missing_fields_rejected_422(client):
    r = client.post("/trades", json={"symbol": "BTC"})
    assert r.status_code == 422