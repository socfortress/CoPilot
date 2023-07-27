import pytest
import json
from copilot import app  # Import your Flask application creation function
from flask_sqlalchemy import SQLAlchemy
from app.models.models import Connectors
from app.models.connectors import ConnectorFactory
from loguru import logger

from app import db  # Import the SQLAlchemy instance from your application

# Add your connector classes here
from app.models.connectors import (
    WazuhIndexerConnector,
    GraylogConnector,
    WazuhManagerConnector,
    DfirIrisConnector,
    VelociraptorConnector,
    RabbitMQConnector,
    ShuffleConnector,
    SublimeConnector,
    InfluxDBConnector,
    AskSOCFortressConnector,
    SocfortressThreatIntelConnector,
)

CONNECTORS = {
    "Wazuh-Indexer": WazuhIndexerConnector,
    "Graylog": GraylogConnector,
    "Wazuh-Manager": WazuhManagerConnector,
    "DFIR-IRIS": DfirIrisConnector,
    "Velociraptor": VelociraptorConnector,
    "RabbitMQ": RabbitMQConnector,
    "Shuffle": ShuffleConnector,
    "Sublime": SublimeConnector,
    "InfluxDB": InfluxDBConnector,
    "AskSocfortress": AskSOCFortressConnector,
    "SocfortressThreatIntel": SocfortressThreatIntelConnector,
}

@pytest.fixture(scope='function')
def setup_connector_factory():
    connector_factory = ConnectorFactory()
    for name, cls in CONNECTORS.items():
        connector_factory.register_creator(name, cls)
    return connector_factory

@pytest.fixture(scope='function')
def client():
    app.config['TESTING'] = True
    with app.test_client() as testing_client:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_copilot.db'  # Use a separate SQLite database for testing
        with app.app_context():
            # Create the database tables
            db.create_all()

            # Insert your test data here
            test_connector = Connectors(
                connector_name="Wazuh-Indexer",
                connector_type="Test Type",
                connector_url="http://localhost:8000",
                connector_username="testuser",
                connector_password="testpass",
                connector_api_key="testapikey"
            )

            db.session.add(test_connector)
            db.session.commit()

            yield testing_client

            # Tear down the database after the tests
            db.drop_all()

def test_list_connectors_available(client):
    response = client.get("/connectors")
    assert response.status_code == 200

    # The response data is a byte string so we need to decode it
    data = json.loads(response.data.decode())

    # Check that the response contains the expected keys
    assert "message" in data
    assert "connectors" in data
    assert "success" in data

    # Check that the 'success' field is True
    assert data["success"] is True

def test_get_connector_details(client, setup_connector_factory):
    # Use setup_connector_factory here
    # Define the id of the connector you want to test
    id = 1  # Modify this value based on your test data

    # Send a GET request to the endpoint
    response = client.get(f'/connectors/{id}')

    # Convert the response data from json to a Python dictionary
    data = json.loads(response.data)

    # Assert that the request got a success response (HTTP status code: 200)
    assert response.status_code == 200

    # Assert that the data has these keys
    assert 'message' in data
    assert 'connector' in data
    assert 'success' in data

    # Assert that success is True
    assert data['success'] is True

def test_get_connector_details_error(client):
    # Define the id of the connector you want to test
    id = 999999  # This should be an ID that does not exist in your test database

    # Send a GET request to the endpoint
    response = client.get(f'/connectors/{id}')

    # Convert the response data from json to a Python dictionary
    data = json.loads(response.data)

    # Assert that the request got a not found response (HTTP status code: 404)
    assert response.status_code == 404

    # Assert that the data has these keys
    assert 'message' in data
    assert 'success' in data

    # Assert that success is False
    assert data['success'] is False

    # Assert that the message is "Connector not found"
    assert data['message'] == "Connector not found"


