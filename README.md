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