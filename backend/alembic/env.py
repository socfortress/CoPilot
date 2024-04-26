from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# from app.db.all_models import *
from app.auth.models.users import User
from app.connectors.models import Connectors

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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
