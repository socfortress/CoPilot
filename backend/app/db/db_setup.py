from loguru import logger
from sqlalchemy import inspect
from sqlmodel import Session
from sqlmodel import SQLModel

# from app.connectors.models import Connectors
# from app.auth.models.users import User
# from app.connectors.wazuh_manager.models.rules import DisabledRule
# from app.agents.models.agents import Agents
# from app.customers.models.customers import Customers
# from app.connectors.sublime.models.alerts import SublimeAlerts
from app.db.all_models import *
from app.db.db_populate import add_connectors_if_not_exist


def create_tables(engine):
    logger.info("Creating tables")

    # Create an inspector object based on the engine
    inspector = inspect(engine)

    # Get the names of all tables in the database
    existing_tables = inspector.get_table_names()

    # Loop through all your models (tables)
    for table in SQLModel.metadata.sorted_tables:
        if table.name not in existing_tables:
            # Only create the table if it doesn't exist
            table.create(bind=engine)
            logger.info(f"Table {table.name} created.")

    # After creating all tables, add connectors if they don't exist
    with Session(engine) as session:
        add_connectors_if_not_exist(session)
        session.commit()
