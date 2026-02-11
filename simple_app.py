from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
def startup():
    logger.info("Application starting up...")

@app.get("/")
def root():
    return {"status": "ok", "message": "MPesa API Docker Test"}

@app.get("/health")
def health():
    return {"healthy": True}
