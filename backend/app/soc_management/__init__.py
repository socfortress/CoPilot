"""SOC Management: SLA tracking and operational metrics for SOC managers (#1187).

Layout follows the clean-architecture split the rest of the backend approximates:

- ``domain/``   — pure rules, no I/O: SLA targets, lifecycle milestones, SLA evaluation,
                  duration statistics, periods and the analytics that turn facts into
                  metrics. Everything here is unit-testable without a database.
- ``models/``   — the three tables this feature owns (SLA policy + per-alert and
                  per-case SLA tracking).
- ``services/`` — application services: recording lifecycle actions, managing policies,
                  loading facts from the database and composing the dashboard/report.
- ``schema/``   — request/response shapes.
- ``routes/``   — thin FastAPI endpoints under ``/api/soc_management``.

The incidents module depends on this one only through
``services/lifecycle.py`` (the recorder its routes call); nothing here mutates an
alert or a case.
"""
