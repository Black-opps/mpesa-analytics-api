# MPesa Analytics API

Production-ready FastAPI service for MPesa transaction analytics.

## Features

- REST API with Swagger
- SQLite persistent storage
- Analytics endpoint
- Dockerized
- Unit tested

## Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
