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
