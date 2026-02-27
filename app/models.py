from pydantic import BaseModel
from typing import Literal


class TradeRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    price: float
    quantity: float


class PnLResponse(BaseModel):
    realized_pnl: float
    unrealized_pnl: float