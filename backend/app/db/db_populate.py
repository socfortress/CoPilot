from app.connectors.models import Connectors
from loguru import logger
from sqlmodel import Session
from datetime import datetime

def add_connectors_if_not_exist(session: Session):
    # List of connectors to add
    connector_list = [
        {"connector_name": "Wazuh-Indexer", "connector_type": "4.4.1", "connector_url": "https://ashwix01.socfortress.local:9200", "connector_username": "admin", "connector_password": "hmx7KPy15XPhJkgjlFrVgrWZ+Aid6QNm", "connector_api_key": None},
        {"connector_name": "Wazuh-Manager", "connector_type": "4.4.1", "connector_url": "https://ashwzhma.socfortress.local:55000", "connector_username": "wazuh-wui", "connector_password": "wazuh-wui", "connector_api_key": None},
        {"connector_name": "Graylog", "connector_type": "5.0.7", "connector_url": "http://ashgrl02.socfortress.local:9000", "connector_username": "socfortress_graylog_manager", "connector_password": "R{2PvE5TQkU7[xS$pX>fw>`y", "connector_api_key": None},
        {"connector_name": "Shuffle", "connector_type": "1.1.0", "connector_url": "https://ASHDKR02.socfortress.local:3443", "connector_username": "sting", "connector_password": "string", "connector_api_key": "bc5d1e18-6230-40f0-b032-6ed898c307c5"},
        {"connector_name": "DFIR-IRIS", "connector_type": "2.0", "connector_url": "https://ashirs01.socfortress.local", "connector_username": None, "connector_password": None, "connector_api_key": "I3Hwvkpvdk8Z0XRFlyGm4WXGw8jksnEzvKNoD9BobtSQ2AgWmdo_p-pfmJCg_ev2cm8I-zgWzAfya3jLBWZ6qw"},
        {"connector_name": "Velociraptor", "connector_type": "0.6.8", "connector_url": "https://ashvlo01.socfortress.local:8001", "connector_username": None, "connector_password": None, "connector_api_key": "C:\\Users\\walto\\Desktop\\GitHub\\CoPilot\\backend\\app\\file-store\\api.config.yaml"},
        {"connector_name": "RabbitMQ", "connector_type": "3", "connector_url": "ashdkr02.socfortress.local:5672", "connector_username": "guest", "connector_password": "guest", "connector_api_key": None},
        {"connector_name": "Sublime", "connector_type": "3", "connector_url": "http://ashdkr02.socfortress.local:8000", "connector_username": None, "connector_password": None, "connector_api_key": "7653trxhakxn4wxdh8bbatbvu97hm8fopos7wztzjrwfd12gf5i2kyebhvke9rt4"},
        {"connector_name": "InfluxDB", "connector_type": "3", "connector_url": "http://ashdkr02.socfortress.local:8086", "connector_username": "SOCFortress", "connector_password": None, "connector_api_key": "gOLoFKucQXXd5d1rDx59YYktIz6OfrHIe4jRowJKZ8iB4IcZES8rOhRPaDEejEkahch8Ze2FiMzZxbQ9ZV8K6g=="},
        {"connector_name": "AskSocfortress", "connector_type": "3", "connector_url": "https://api.socfortress.co/rule", "connector_username": None, "connector_password": None, "connector_api_key": "CkKmw1B9NM1hG669tC4sTazLm1HlRfSXVvMZkxa9"},
        {"connector_name": "SocfortressThreatIntel", "connector_type": "3", "connector_url": "https://intel.socfortress.co/search", "connector_username": None, "connector_password": None, "connector_api_key": "ozH1jHp1zmacCePYrAZmxarJCGptcMth93a86Jq8"},
        {"connector_name": "Cortex", "connector_type": "3", "connector_url": "http://ashvlo01.socfortress.local:9001", "connector_username": None, "connector_password": None, "connector_api_key": "+k/DvVYMEYURbc8sUdXA5/hW9VhJZV3v"}
    ]

    for connector_data in connector_list:
        # Check if connector already exists in the database
        existing_connector = session.query(Connectors).filter_by(connector_name=connector_data["connector_name"]).first()
        
        if existing_connector is None:
            # If connector does not exist, create new connector entry
            new_connector = Connectors(**connector_data)
            session.add(new_connector)
            logger.info(f"Added new connector: {connector_data['connector_name']}")
    
    # Commit the changes if any new connectors were added
    session.commit()
