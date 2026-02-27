from dataclasses import dataclass
from typing import List, Dict, Optional
from decimal import Decimal

from fastapi.exceptions import HTTPException


@dataclass
class Trade:
    id: int
    symbol: str
    side: str  # "buy" or "sell"
    price: Decimal
    quantity: Decimal
    reference_id: Optional[int] = None  # for sell trades


class PortfolioEngine:
    def __init__(self):
        self.trades: List[Trade] = []
        self._trade_counter = 1

    # -------------------------
    # BUY
    # -------------------------

    def buy(self, symbol: str, price: float, quantity: float) -> int:
        trade = Trade(
            id=self._trade_counter,
            symbol=symbol,
            side="buy",
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
        )
        self._trade_counter += 1
        self.trades.append(trade)
        return trade.id

    # -------------------------
    # SELL (FIFO enforced)
    # -------------------------

    def sell(self, symbol: str, price: float, quantity: float):
        price = Decimal(str(price))
        quantity = Decimal(str(quantity))

        remaining = quantity

        open_buys = self._get_open_buys(symbol)

        total_available = sum(qty for _, qty in open_buys)

        if remaining > total_available:
            raise HTTPException(status_code=400, detail="Not enough quantity to sell")

        for buy_trade, remaining_qty in open_buys:
            if remaining == 0:
                break

            sell_qty = min(remaining, remaining_qty)

            sell_trade = Trade(
                id=self._trade_counter,
                symbol=symbol,
                side="sell",
                price=price,
                quantity=sell_qty,
                reference_id=buy_trade.id,
            )
            self._trade_counter += 1
            self.trades.append(sell_trade)

            remaining -= sell_qty

    # -------------------------
    # Portfolio
    # -------------------------

    def get_portfolio(self):
        result = {}

        for trade in self.trades:
            if trade.side == "buy":
                remaining = self._remaining_quantity(trade.id)

                if remaining > 0:
                    symbol = trade.symbol

                    if symbol not in result:
                        result[symbol] = {
                            "total_quantity": Decimal("0"),
                            "total_cost": Decimal("0"),
                        }

                    result[symbol]["total_quantity"] += remaining
                    result[symbol]["total_cost"] += remaining * trade.price

        # Compute average entry price
        final = {}

        for symbol, data in result.items():
            total_qty = data["total_quantity"]
            total_cost = data["total_cost"]

            avg_price = total_cost / total_qty if total_qty > 0 else Decimal("0")

            final[symbol] = {
                "quantity": float(total_qty),
                "average_entry_price": float(avg_price),
            }

        return final

    # -------------------------
    # PnL
    # -------------------------

    def get_pnl(self, latest_prices: Dict[str, float]):
        realized = Decimal("0")
        unrealized = Decimal("0")

        for trade in self.trades:
            if trade.side == "sell":
                buy_trade = self._get_trade_by_id(trade.reference_id)
                realized += (trade.price - buy_trade.price) * trade.quantity

        for trade in self.trades:
            if trade.side == "buy":
                remaining = self._remaining_quantity(trade.id)
                if remaining > 0:
                    current_price = Decimal(str(latest_prices.get(trade.symbol, 0)))
                    unrealized += (current_price - trade.price) * remaining

        return {
            "realized_pnl": float(realized),
            "unrealized_pnl": float(unrealized),
        }

    # -------------------------
    # Helpers & Internal utilities
    # -------------------------

    def _get_open_buys(self, symbol: str):
        """
        Returns list of tuples:
        [(buy_trade, remaining_quantity), ...]
        in FIFO order
        """
        buys = [
            trade for trade in self.trades
            if trade.symbol == symbol and trade.side == "buy"
        ]

        result = []

        for buy in buys:
            sold_qty = sum(
                t.quantity for t in self.trades
                if t.side == "sell" and t.reference_id == buy.id
            )
            remaining = buy.quantity - sold_qty
            if remaining > 0:
                result.append((buy, remaining))

        return result

    def _remaining_quantity(self, buy_id: int) -> Decimal:
        buy_trade = self._get_trade_by_id(buy_id)

        sold_qty = sum(
            t.quantity for t in self.trades
            if t.side == "sell" and t.reference_id == buy_id
        )

        return buy_trade.quantity - sold_qty

    def _get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        for trade in self.trades:
            if trade.id == trade_id:
                return trade
        return None