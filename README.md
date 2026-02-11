# MPesa Analytics API

[![GitHub stars](https://img.shields.io/github/stars/Black-opps/mpesa-analytics-api?style=social)]()
[![GitHub forks](https://img.shields.io/github/forks/Black-opps/mpesa-analytics-api?style=social)]()
[![Python](https://img.shields.io/badge/Python-3.12-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-green)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()


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
