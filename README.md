# CoPilot

SOCFortress CoPilot is developed using python 3.11. It'll likely work in earlier versions, but we're targeting
3.11 for the extra error reporting featurest that dropped in 3.10 and later.

# Development

SOCFortress CoPilot is developed using python 3.11. It'll likely work in earlier versions, but we're targeting
3.11 for the extra error reporting featurest that dropped in 3.10 and later.

## Local development of backend

Setup the env vars, adjust if required, such as the `UPLOAD_FOLDER` environment variable.

```
cd backend
cp .env.example .env
```

Create and activate python.

### macOS/Linux

```
python3.11 -m venv .venv --copies
source .venv/bin/activate
```

### Windows

```
python.exe -m venv .venv --copies
.venv\Scripts\activate
```

Installing dependencies

```
pip install -U pip setuptools wheel
pip install -r requirements.in
```

Create a DB and apply any pending DB migrations

```
FLASK_APP=copilot.py flask db upgrade
```

If requiring to connect to the

```
sqlite3 copilot.db < insert_data.sql
```

Start local dev server

```
python app.py
```

## Test local backend

Show configured connectors

```
curl http://localhost:5000/connectors
```

## Database changes

If there any changes made to the model first ensure that it is added to the list of imports in
`backend/app/__init_.py` before the following line

```
migrate = Migrate(app, db)
```

This allows alembic and flask migrate to see all the models in use so the migrations can be
generated correctly.

Once that is done, then you need to run the migrate command (example commment)
and if any changes were detected, update your local DB instance.

```
FLASK_APP=copilot.py flask db migrate -m "Add User model."
FLASK_APP=copilot.py flask db upgrade
```

Review the generated migration file to make sure the changes to the databse make sense in terms
of what is needed to upgrade from the previous state, and then to downgrade to remove this migration.

Don't forget to commit the new migration file into git.

See https://flask-migrate.readthedocs.io/en/latest/ for further information

# Deployment

## Production Deployment Notes

```
pip install -r requirements.txt
```
