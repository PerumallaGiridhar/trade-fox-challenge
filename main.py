from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from app.routes import router


app = FastAPI()


app.include_router(router)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.get("/ready")
async def server_liveness():
    return {"status": "running"}