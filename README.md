# HealLink

Backend setup (FastAPI + Clean Architecture starter).

## Project structure

```text
app/
  core/       # app configuration
  db/         # database base and sessions
  models/     # SQLAlchemy models
  routers/    # FastAPI route handlers
  schemas/    # Pydantic request/response models
  services/   # business logic layer
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python run.py
```

Open: `http://localhost:8000/docs`

## Environment variables

Set database connection in `.env`:

```bash
DATABASE_URL=postgresql://user:password@host:5432/db_name
JWT_SECRET_KEY=replace-with-a-long-random-secret
```

## First domain endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/patients/me` (Bearer token required)
- `GET /api/v1/appointments/services`
- `POST /api/v1/appointments` (Bearer token required)
- `GET /api/v1/appointments/mine` (Bearer token required)
- `POST /api/v1/appointments/{appointment_id}/cancel` (Bearer token required)

## Database migrations (Alembic)

Run migrations:

```bash
alembic upgrade head
```

Create a new migration after model changes:

```bash
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

## Makefile shortcuts

```bash
make venv
make install
make dev
make migrate
make revision MSG="add appointments table"
```
