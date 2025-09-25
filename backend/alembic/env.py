# import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import ssl
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine.url import make_url
from sqlmodel import SQLModel

from alembic import context

# from app.db.all_models import *
from app.auth.models.users import User
from app.connectors.models import Connectors
from app.connectors.wazuh_indexer.models.sigma import SigmaQuery

# from app.integrations.sap_siem.models.sap_siem import SapSiemMultipleLogins
from app.customer_provisioning.models.default_settings import (
    CustomerProvisioningDefaultSettings,
)

# from app.connectors.sublime.models.alerts import SublimeAlerts
# from app.connectors.wazuh_manager.models.rules import DisabledRule
from app.db.universal_models import Agents
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta
from app.db.universal_models import LogEntry
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertTitleFieldName
from app.incidents.models import AlertToIoC
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import AssetFieldName
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import CaseDataStore
from app.incidents.models import CaseReportTemplateDataStore
from app.incidents.models import Comment
from app.incidents.models import CustomerCodeFieldName
from app.incidents.models import FieldName
from app.incidents.models import IoC
from app.incidents.models import IoCFieldName
from app.incidents.models import Notification
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.models.customer_integration_settings import CustomerIntegrations
from app.integrations.monitoring_alert.models.monitoring_alert import MonitoringAlerts
from app.network_connectors.models.network_connectors import AvailableNetworkConnectors
from app.network_connectors.models.network_connectors import (
    AvailableNetworkConnectorsKeys,
)
from app.network_connectors.models.network_connectors import CustomerNetworkConnectors
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)
from app.network_connectors.models.network_connectors import NetworkConnectorsConfig
from app.network_connectors.models.network_connectors import NetworkConnectorsService
from app.network_connectors.models.network_connectors import (
    NetworkConnectorsSubscription,
)
from app.schedulers.models.scheduler import JobMetadata
from settings import DB_TLS
from settings import DB_TLS_CA
from settings import TLS_VERIFY

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _tls_connect_args_for_url(url_str: str) -> dict:
    """
    Build connect_args for TLS only when using a MySQL driver.
    Uses settings.py: DB_TLS, TLS_VERIFY, DB_TLS_CA.
    """
    if not DB_TLS:
        return {}
    try:
        drivername = make_url(url_str).drivername  # e.g., 'mysql+pymysql'
    except Exception:
        drivername = ""
    if not drivername.startswith("mysql"):
        return {}

    if TLS_VERIFY:
        ctx = ssl.create_default_context(cafile=DB_TLS_CA or None)
        ctx.check_hostname = True
    else:
        ctx = ssl._create_unverified_context()
        ctx.check_hostname = False
    return {"ssl": ctx}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# def run_migrations_online() -> None:
#     """Run migrations in 'online' mode.

#     In this scenario we need to create an Engine
#     and associate a connection with the context.

#     """
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section, {}),
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(connection=connection, target_metadata=target_metadata)

#         with context.begin_transaction():
#             context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    url = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_tls_connect_args_for_url(url),  # --- minimal TLS hook ---
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
