<div align="center">
  <h1>MPesa Analytics API</h1>
  <p><strong>A production-ready FastAPI service for transforming MPesa transaction data into actionable business intelligence.</strong></p>

  <!-- Add your status badges here if you have any -->
  <p>
    <img src="https://img.shields.io/badge/FastAPI-0.128.0-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python" alt="Python">
    <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy" alt="SQLAlchemy">
    <img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker" alt="Docker">
  </p>
</div>

---

## 👋 **Overview**

The **MPesa Analytics API** is a secure, scalable, and feature-rich backend solution built with **FastAPI**. It goes beyond simple transaction logging, providing a robust platform for businesses to gain deep insights from their financial data. With built-in role-based access control, it's perfect for both individual users and enterprise-level management.

This API serves as the powerful engine for a modern fintech dashboard, enabling data-driven decisions through comprehensive analytics endpoints.

## ✨ **Key Features**

*   **🔐 Role-Based Access Control (RBAC)**
    *   **Regular Users**: Experience complete data isolation, viewing and analyzing only their own transactions.
    *   **Administrators**: Gain a holistic view with the ability to manage all users, view system-wide analytics, and oversee platform operations.
*   **📊 Comprehensive Analytics Endpoints**
    *   Generate key business metrics instantly: `total_sent`, `total_received`, `transaction_count`, and `unique_customers`.
    *   Analyze trends with daily, weekly, or monthly aggregates.
    *   Break down transactions by type for a clear picture of business activity.
*   **🔒 Enterprise-Grade Security**
    *   **JWT Authentication**: Secure, token-based user sessions.
    *   **Row-Level Security**: Enforced at the database query level, guaranteeing that users can only access their own data.
    *   **Password Hashing**: Industry-standard bcrypt for credential safety.
*   **👑 Powerful Admin Capabilities**
    *   Dedicated admin routes for user management (create, view, toggle status, delete).
    *   System-wide analytics endpoint to monitor the entire platform's health and performance.
*   **🚀 Production-Ready Architecture**
    *   **Fully Dockerized**: Easy setup and deployment with Docker Compose.
    *   **SQLite Persistent Storage**: Simple, file-based database perfect for MVPs and scalable projects.
    *   **Self-Documenting API**: Interactive Swagger UI and ReDoc available at `/docs` and `/redoc`.
    *   **Extensive Logging & Error Handling**: Built for reliability and easy debugging.

## 🛠️ **Technology Stack**

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API Framework** | FastAPI | High-performance, async-capable web framework with automatic OpenAPI docs. |
| **Authentication** | JWT + OAuth2 | Secure, stateless user authentication with role-based payloads. |
| **Database ORM** | SQLAlchemy 2.0 | Powerful and flexible ORM for database interactions. |
| **Database** | SQLite | Lightweight, serverless database for persistent storage. |
| **Security** | passlib[bcrypt] | Secure password hashing. |
| **Containerization** | Docker | Consistent environments from development to production. |
| **Language** | Python 3.12+ | Modern Python with full type hinting support. |

## 📂 **Project Structure**
mpesa-analytics-api/
├── app/
│ ├── init.py
│ ├── main.py # FastAPI application entry point, CORS, middleware
│ ├── core/ # Core configurations and security
│ │ ├── init.py
│ │ ├── database.py # Database engine and session management
│ │ └── security.py # JWT handling, password hashing, auth dependencies
│ ├── models/ # SQLAlchemy ORM models
│ │ ├── init.py
│ │ ├── user.py # User model with role and status
│ │ └── transaction.py # Transaction model
│ ├── routers/ # API route handlers (versioned)
│ │ ├── init.py
│ │ ├── auth.py # Authentication endpoints (/auth)
│ │ ├── users.py # User profile endpoints (/users)
│ │ ├── admin.py # Admin-only endpoints (/admin)
│ │ ├── analytics.py # Analytics endpoints (/analytics)
│ │ └── transactions.py # Transaction endpoints (/transactions)
│ ├── schemas/ # Pydantic models for request/response validation
│ │ ├── init.py
│ │ ├── user.py
│ │ ├── transaction.py
│ │ ├── analytics.py
│ │ └── token.py
│ └── services.py # Core business logic layer
├── data/ # SQLite database file location (git-ignored)
├── scripts/ # Utility and management scripts
│ ├── reset_db.py # Reset and seed the database
│ ├── check_db.py # Inspect database contents
│ ├── add_test_data.py # Generate test transactions
│ └── list_users.py # List all users in the system
├── requirements.txt # Python dependencies
├── Dockerfile # Docker build instructions
├── docker-compose.yml # Local Docker setup
├── .env.example # Example environment variables
└── start.ps1 # Convenience start script for Windows


##  **Quick Start (5 Minutes)**

Get the API up and running locally.

### **Prerequisites**
*   Python 3.12+
*   Docker and Docker Compose (optional, for containerized run)

### **Installation & Setup**

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Black-opps/mpesa-analytics-api.git
    cd mpesa-analytics-api

### **Run with Docker**
docker-compose up --build
