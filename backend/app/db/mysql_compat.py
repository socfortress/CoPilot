"""MySQL 8.4 compatibility for CoPilot's schema migrations.

CoPilot's foreign keys to ``customers.customer_code`` and ``agents.agent_id`` point at
indexes that are not unique (both tables' primary key is ``id``). MySQL 8.4 deprecates such
keys and, while ``restrict_fk_on_non_standard_key`` is ON (its default), refuses to create one
(ERROR 6125) and refuses every ALTER TABLE on a table they point at (ERROR 1553). Existing keys
keep working after an upgrade, but a fresh install stops at the first migration, and on an
upgraded database the next migration that adds such a key, or alters ``customers`` or
``agents``, stops the backend at startup.

A session may switch that check off, so every connection Alembic opens does so before it
migrates. MySQL 8.0 and MariaDB have no such variable, and nothing is done there. Only the
migrations' connections change: the application's own never run DDL.

The durable fix is a UNIQUE key on both columns, after which the keys are standard and this
setting no longer matters to them.
"""

from loguru import logger
from sqlalchemy import event
from sqlalchemy.engine import Engine

FK_RESTRICTION = "restrict_fk_on_non_standard_key"


def relax_fk_restriction(dbapi_connection) -> bool:
    """Switch the restriction off for this DBAPI connection's session.

    Returns True when the server had it on and it is now off; False when the server has no
    such variable (MySQL before 8.4, MariaDB) or it was already off.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SHOW SESSION VARIABLES LIKE '{FK_RESTRICTION}'")
        row = cursor.fetchone()
        if not row or str(row[1]).upper() != "ON":
            return False
        cursor.execute(f"SET SESSION {FK_RESTRICTION} = OFF")
        return True
    finally:
        cursor.close()


def _relax_on_connect(dbapi_connection, _connection_record) -> None:
    try:
        if relax_fk_restriction(dbapi_connection):
            logger.info(f"MySQL: {FK_RESTRICTION} switched off for this migration session")
    except Exception as e:  # migrations then run exactly as they would without this hook
        logger.warning(f"MySQL: could not switch {FK_RESTRICTION} off for migrations: {type(e).__name__}: {e}")


def install_fk_relaxation(engine: Engine) -> None:
    """Have every new connection of ``engine`` allow foreign keys to non-unique keys.

    For Alembic's engine (``alembic/env.py``). A no-op for any database but MySQL, and when
    already installed on this engine.
    """
    if engine.dialect.name != "mysql":
        return
    if not event.contains(engine, "connect", _relax_on_connect):
        event.listen(engine, "connect", _relax_on_connect)
