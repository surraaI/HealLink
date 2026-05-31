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
pip install -r requirements.txt
pip install -e .
python run.py
```

Open: `http://localhost:8000/docs`

## Environment variables

Set database connection in `.env`:

```bash
DATABASE_URL=postgresql://user:password@host:5432/db_name
JWT_SECRET_KEY=replace-with-a-long-random-secret
CHAPA_SECRET_KEY=CHASECK-xxxxxxxxxxxxxxxx
CHAPA_PUBLIC_KEY=CHAPUBK-xxxxxxxxxxxxxxxx
CHAPA_CALLBACK_URL=https://your-api.example.com/api/v1/payments/chapa/callback
CHAPA_RETURN_URL=https://your-frontend.example.com/payment/return
```

Patient notifications use an **in-app inbox** plus **optional email** through SMTP when enabled. SMS is intentionally not part of this notification layer.

Optional email delivery:

```bash
NOTIFICATIONS_EMAIL_ENABLED=true
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@example.com
ACCOUNT_ACTION_TOKEN_EXPIRE_HOURS=24
```

## First domain endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `GET /api/v1/patients/me` (Bearer token required)
- `PATCH /api/v1/patients/me` (Bearer token required)
- `GET /api/v1/appointments/services`
- `POST /api/v1/appointments` (Bearer token required)
- `GET /api/v1/appointments/mine` (Bearer token required)
- `POST /api/v1/appointments/{appointment_id}/cancel` (Bearer token required)
- `GET /api/v1/notifications/mine` (Bearer token required)
- `POST /api/v1/notifications/{notification_id}/read` (Bearer token required)
- `GET /api/v1/providers`
- `POST /api/v1/providers`
- `POST /api/v1/providers/{provider_id}/services`
- `POST /api/v1/providers/services/{service_id}/slots`
- `GET /api/v1/providers/services/{service_id}/slots`
- `POST /api/v1/providers/{provider_id}/appointments/{appointment_id}/complete`
- `POST /api/v1/providers/{provider_id}/appointments/{appointment_id}/needs-recheck`
- `POST /api/v1/providers/{provider_id}/appointments/{appointment_id}/book-recheck`

After a visit, a provider may mark **`needs-recheck`** (clinical issue not resolved); the patient is notified and a new slot can be booked with **`book-recheck`**, which links follow-up appointments to the original visit.

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
