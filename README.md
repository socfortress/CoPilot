# CoPilot

SOCFortress CoPilot

# Development

## Local development of backend

Setup the env vars, adjust if required.

```
cd backend
cp .env.example .env
```

Create and activate python, installing dependencies

```
python3.11 -m venv.venv --copies
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.in
```

Create a DB and apply any pending DB migrations

```
FLASK_APP=copilot.py flask db upgrade
```

Start local dev server

```
python3 app.py
```

If there any changes made to the model run the migrate command (example commment)
and if any changes were detected, update your local DB instance.

```
FLASK_APP=copilot.py flask db migrate -m "Add User model."
FLASK_APP=copilot.py flask db upgrade
```

See https://flask-migrate.readthedocs.io/en/latest/ for further information

# Deployment

## Production Deployment Notes

```
pip install -r requirements.txt
```
