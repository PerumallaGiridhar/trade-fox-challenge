from pydantic import BaseModel
from typing import Literal


class TradeRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    price: float
    quantity: float
    