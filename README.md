# Cowork Management API (Backend)

This is the backend service for the **Cowork Management System**, built using FastAPI and PostgreSQL. It serves as the core API for managing students, projects, and their respective assignments.

## 🚀 Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Language**: Python 3
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **Database**: PostgreSQL
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **Authentication**: JWT (JSON Web Tokens) stored in HttpOnly cookies
- **Cloud/Storage**: AWS S3 (for student avatars and media)

## 📁 Project Structure

```text
backend/
├── src/
│   ├── api/            # API routers and endpoints
│   ├── core/           # Core settings, middleware, and logging
│   ├── database/       # Database session and configuration
│   ├── models/         # SQLAlchemy database models
│   ├── repository/     # Data access layer (CRUD operations)
│   ├── schemas/        # Pydantic models for request/response validation
│   ├── services/       # Business logic and use cases
│   ├── utils/          # Helper functions (security, exceptions, etc.)
│   ├── config.py       # Environment variable configurations
│   └── main.py         # FastAPI application entry point
├── migrations/         # Alembic migration scripts
├── alembic.ini         # Alembic configuration file
├── requirements.txt    # Python dependencies
└── .env                # Environment variables (do not commit)
```

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- PostgreSQL server running locally or remotely

### 2. Environment Setup
Clone the repository and navigate to the `backend` directory.

Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the `backend/` directory. You can use the following template:

```env
APP_ENV=development
PORT=8000
DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/cowork_db
JWT_SECRET_KEY=your-super-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=1440
COOKIE_NAME=access_token
CORS_ORIGIN=http://localhost:3000
```

### 4. Database Migrations
Ensure your PostgreSQL database (e.g., `cowork_db`) is created. Then, run the Alembic migrations to create the tables:

```bash
alembic upgrade head
```

### 5. Seeding the Database
You can populate the database with initial dummy users (both Admins and Staffs) by running the seed script:

```bash
python src/database/seed_users.py
```

This will create test accounts, for example:
- `adminexample1@gmail.com` / `password123` (Admin)
- `staffexample1@gmail.com` / `password123` (Staff)

### 6. Running the Application
Start the FastAPI development server using Uvicorn:

```bash
uvicorn src.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. 
- Interactive API Documentation (Swagger UI): `http://localhost:8000/docs`
- ReDoc Documentation: `http://localhost:8000/redoc`

## 🔐 Authentication & RBAC
The API uses cookie-based JWT authentication. Upon successful login (`POST /api/v1/auth/login`), an `HttpOnly` cookie is set in the client's browser. Subsequent requests will automatically include this cookie. Ensure `CORS_ORIGIN` is configured correctly to allow credentials (cookies) to be sent from your frontend domain.

The system enforces **Role-Based Access Control (RBAC)**:
- **Admin** (`role = 'admin'`): Has full access to create, update, and delete records (Students, Projects, and Users).
- **Staff** (`role = 'staff'`): Has read-only access (view records). Write operations (`POST`, `PUT`, `DELETE`) will return `403 Forbidden`.
