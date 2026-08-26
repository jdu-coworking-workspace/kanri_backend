# Cowork Management API (Backend)

Backend service for the **Cowork Management System**, built with FastAPI and PostgreSQL.

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.10+) |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Migrations | Alembic |
| Authentication | JWT via HttpOnly cookie |
| Storage (local) | `backend/media/` folder (served at `/media`) |
| Storage (production) | AWS S3 |

---

## ⚙️ Local Setup (Step by Step)

### 1. Prerequisites
- Python **3.10+**
- **PostgreSQL** server running locally

### 2. Create virtual environment

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` file

Create a `.env` file inside the `backend/` directory:

```env
APP_ENV=development
PORT=8000
DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/cowork_db
TEST_DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/cowork_test_db
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=1440
COOKIE_NAME=access_token
CORS_ORIGIN=http://localhost:3000

# Storage mode: "local" (saves to backend/media/) or "production" (uploads to AWS S3)
S3_MODE=local

# AWS S3 — only needed when S3_MODE=production
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-northeast-1
AWS_S3_BUCKET_NAME=cowork-media
```

> **Note:** For local development, keep `S3_MODE=local`. Avatar images will be saved to `backend/media/` and served at `http://localhost:8000/media/...`.

### 5. Create the database

Open `psql` or any PostgreSQL client and run:

```sql
CREATE DATABASE cowork_db;
```

### 6. Run migrations

```bash
alembic upgrade head
```

### 7. Seed initial users

Populates the database with **2 admin** and **4 staff** accounts:

```bash
python src/database/seed_users.py
```

Default accounts created:

| Email | Password | Role |
|---|---|---|
| adminexample1@gmail.com | password123 | admin |
| adminexample2@gmail.com | password123 | admin |
| staffexample1@gmail.com | password123 | staff |
| staffexample2@gmail.com | password123 | staff |
| staffexample3@gmail.com | password123 | staff |
| staffexample4@gmail.com | password123 | staff |

### 8. Start the server

```bash
uvicorn src.main:app --reload --port 8000
```

The server will be available at:

| URL | Description |
|---|---|
| `http://localhost:8000/` | Health check |
| `http://localhost:8000/docs` | **Swagger UI** (interactive API docs) |
| `http://localhost:8000/redoc` | ReDoc documentation |
| `http://localhost:8000/media/` | Static media files (local mode only) |

---

## 📋 API Endpoints (Summary)

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | Login (sets cookie) |
| POST | `/api/v1/auth/logout` | Auth | Logout (clears cookie) |
| GET | `/api/v1/auth/me` | Auth | Current user info |
| GET | `/api/v1/projects/` | Auth | List projects (filter + pagination) |
| POST | `/api/v1/projects/` | Admin | Create project |
| GET | `/api/v1/projects/{id}` | Auth | Project detail |
| PUT | `/api/v1/projects/{id}` | Admin | Update project |
| DELETE | `/api/v1/projects/{id}` | Admin | Delete project |
| GET | `/api/v1/projects/{id}/history` | Auth | Project change history |
| POST | `/api/v1/projects/{id}/members` | Admin | Add member (max 8) |
| DELETE | `/api/v1/projects/{id}/members/{student_id}` | Admin | Remove member |
| PATCH | `/api/v1/projects/{id}/members/{student_id}/move` | Admin | Move member (drag & drop) |
| GET | `/api/v1/students` | Auth | List students (`?q=` search) |
| POST | `/api/v1/students` | Admin | Create student |
| GET | `/api/v1/students/{id}` | Auth | Student detail + history |
| PUT | `/api/v1/students/{id}` | Admin | Update student |
| DELETE | `/api/v1/students/{id}` | Admin | Delete student |
| POST | `/api/v1/students/{id}/copy` | Admin | Copy student |
| GET | `/api/v1/students/{id}/history` | Auth | Student project history |
| POST | `/api/v1/uploads/avatar` | Admin | Upload avatar (multipart/form-data) |
| GET | `/api/v1/users/` | Admin | List users |
| POST | `/api/v1/users/` | Admin | Create user |
| PUT | `/api/v1/users/{id}/role` | Admin | Change user role |
| DELETE | `/api/v1/users/{id}` | Admin | Delete user |

---

## 🔐 Authentication & RBAC

Authentication uses **cookie-based JWT** (`HttpOnly`). After `POST /api/v1/auth/login`, the browser automatically sends the cookie with every request.

| Role | Permissions |
|---|---|
| **admin** | Full access: create, update, delete all records |
| **staff** | Read-only: `GET` endpoints only. `POST/PUT/DELETE` → `403 Forbidden` |

---

## 🧪 Running Tests

Tests use a separate PostgreSQL database (configured via `TEST_DATABASE_URL` in `.env`).

```bash
PYTHONPATH=. pytest
```

> 141 tests — all passing ✅

---

## 📁 Project Structure

```text
backend/
├── src/
│   ├── api/v1/         # Routers: auth, students, projects, users, uploads
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic request/response schemas
│   ├── services/       # Business logic
│   ├── repository/     # Database queries
│   ├── utils/          # security.py, s3.py (storage)
│   ├── database/       # session.py, seed_users.py
│   ├── config.py       # Settings (reads from .env)
│   └── main.py         # App entry point
├── migrations/         # Alembic migration files
├── media/              # Local avatar storage (S3_MODE=local only)
├── alembic.ini
├── requirements.txt
└── .env
```
