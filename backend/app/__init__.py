from flask import Flask
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_swagger_ui import get_swaggerui_blueprint

# from app.routes import bp  # Import the blueprint

app = Flask(__name__)

SWAGGER_URL = "/api/docs"  # URL for exposing Swagger UI (without trailing '/')
API_URL = "/static/swagger.json"  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,  # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
    API_URL,
    config={"app_name": "Test application"},  # Swagger UI config overrides
    # oauth_config={  # OAuth config. See https://github.com/swagger-api/swagger-ui#oauth2-configuration .
    #    'clientId': "your-client-id",
    #    'clientSecret': "your-client-secret-if-required",
    #    'realm': "your-realms",
    #    'appName': "your-app-name",
    #    'scopeSeparator': " ",
    #    'additionalQueryStringParams': {'test': "hello"}
    # }
)

app.register_blueprint(swaggerui_blueprint)

CORS(app)


app.config.from_object("settings")

db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

from app.routes.connectors import bp as connectors_bp  # Import the blueprint
from app.routes.agents import bp as agents_bp  # Import the blueprint
from app.routes.rules import bp as rules_bp  # Import the blueprint
from app.routes.graylog import bp as graylog_bp  # Import the blueprint
from app.routes.alerts import bp as alerts_bp  # Import the blueprint
from app.routes.wazuhindexer import bp as wazuhindexer_bp  # Import the blueprint
from app.routes.shuffle import bp as shuffle_bp  # Import the blueprint
from app.routes.velociraptor import bp as velociraptor_bp  # Import the blueprint
from app.routes.dfir_iris import bp as dfir_iris_bp  # Import the blueprint

app.register_blueprint(connectors_bp)  # Register the connectors blueprint
app.register_blueprint(agents_bp)  # Register the agents blueprint
app.register_blueprint(rules_bp)  # Register the rules blueprint
app.register_blueprint(graylog_bp)  # Register the graylog blueprint
app.register_blueprint(alerts_bp)  # Register the alerts blueprint
app.register_blueprint(wazuhindexer_bp)  # Register the wazuhindexer blueprint
app.register_blueprint(shuffle_bp)  # Register the shuffle blueprint
app.register_blueprint(velociraptor_bp)  # Register the velociraptor blueprint
app.register_blueprint(dfir_iris_bp)  # Register the dfir_iris blueprint
