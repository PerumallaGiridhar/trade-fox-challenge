from fastapi import APIRouter 
from app.engine import PortfolioEngine
from app.models import TradeRequest
from app.prices import LATEST_PRICES


router = APIRouter()
engine = PortfolioEngine()


@router.post("/trades")
def add_trade(trade: TradeRequest):
    if trade.side == "buy":
        engine.buy(trade.symbol, trade.price, trade.quantity)
    else:
        engine.sell(trade.symbol, trade.price, trade.quantity)
    
    return {"status": "ok"}


@router.get("/portfolio")
def get_portfolio():
    return engine.get_portfolio()


@router.get("/pnl")
def get_pnl():
    return engine.get_pnl(LATEST_PRICES)