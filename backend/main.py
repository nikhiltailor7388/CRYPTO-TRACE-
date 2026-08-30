import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import auth, cases, reports, routes, trace_impl

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("cryptotrace")

app = FastAPI(title="CryptoTrace - Backend Skeleton")

# Allow CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info("request %s %s completed in %.1f ms with status %s", request.method, request.url.path, elapsed, response.status_code)
    return response

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(routes.router)
app.include_router(reports.router)
app.include_router(trace_impl.router)

@app.get("/health")
def health():
    return {"status": "ok"}
