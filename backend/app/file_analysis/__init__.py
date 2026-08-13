"""CoPilot File Analysis feature module (issue #974).

Two-tier file analysis: static inspection always (Tier 1), pluggable detonation
off by default (Tier 2, ``SANDBOX_BACKEND=none|local_vm|remote``).

This package deliberately adds **no SQLModel tables and no migrations** — all
state (jobs, cached results, previews) is persisted as objects in MinIO via
``services/state_store.py``, so the feature ships without a schema change.
See the "File Analysis module" section of the repo-root CLAUDE.md.
"""
