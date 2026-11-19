"""Deploying the SonicWall network connector over TLS or UDP.

The connector used to create one input, syslog over TCP with TLS, whatever the request said. UDP adds
`SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP`, made from the SOCFortress SonicWall content pack (Aug 2023):
its extractors split SonicWall's key=value pairs and derive `src_ip`, `dst_ip`, `msg_cat` and
`msg_detail`, the fields the SonicWall dashboards read. These tests pin:

- which transport a deploy request asks for, and that TLS stays the default;
- that only the chosen input's content pack is installed, without changing what any other network
  connector or integration installs;
- that the names the service looks the input up by match what the templates create;
- that the UDP input lands in the customer's stream and keeps the extractors' order.

No DB, no network.

Run with: cd backend && python -m pytest tests/test_sonicwall_network_connector.py
"""

import asyncio
import json
import os
import re
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.connectors.graylog.schema.pipelines import PipelineRule  # noqa: E402
from app.connectors.graylog.schema.pipelines import PipelineRulesResponse  # noqa: E402
from app.stack_provisioning.graylog.routes import sonicwall as sonicwall_routes  # noqa: E402
from app.stack_provisioning.graylog.schema.provision import (  # noqa: E402
    AvailableContentPacks,
)
from app.stack_provisioning.graylog.schema.provision import (  # noqa: E402
    ContentPackKeywords,
)
from app.stack_provisioning.graylog.schema.provision import (  # noqa: E402
    ProvisionNetworkContentPackRequest,
)
from app.stack_provisioning.graylog.schema.provision import (  # noqa: E402
    ReplaceContentPackKeywords,
)
from app.stack_provisioning.graylog.schema.sonicwall import (  # noqa: E402
    ProvisionSonicwallRequest,
)
from app.stack_provisioning.graylog.schema.sonicwall import (  # noqa: E402
    SonicwallProtocol,
)
from app.stack_provisioning.graylog.services import provision as provision_service  # noqa: E402
from app.stack_provisioning.graylog.services import sonicwall as sonicwall_service  # noqa: E402

CUSTOMER_NAME = "Example Customer"
CUSTOMER_CODE = "example01"
PLACEHOLDERS = ("customer_name", "customer_code", "SYSLOG_PORT", "TLS_CERT_FILE", "TLS_KEY_FILE", "REPLACE_UUID")


def run(coroutine):
    return asyncio.run(coroutine)


def request(**flags):
    return ProvisionSonicwallRequest(customer_code=CUSTOMER_CODE, hot_data_retention=30, index_replicas=1, **flags)


def keys(port="5514", cert="", key=""):
    return {"SYSLOG_PORT": port, "TLS_CERT_FILE": cert, "TLS_KEY_FILE": key}


def values(obj):
    """A content pack entity's data with the `{"@type", "@value"}` wrappers removed."""
    if isinstance(obj, dict) and "@value" in obj:
        return obj["@value"]
    if isinstance(obj, dict):
        return {k: values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [values(v) for v in obj]
    return obj


def installed_template(name, protocol=SonicwallProtocol.UDP, port=5514):
    """A template as `process_content_pack` installs it for the customer."""
    pack = provision_service.load_content_pack_json(f"{name}.json")
    replacements = ReplaceContentPackKeywords(
        REPLACE_UUID_GLOBAL="11111111-1111-4111-8111-111111111111",
        REPLACE_UUID_SPECIFIC="22222222-2222-4222-8222-222222222222",
        customer_name=CUSTOMER_NAME,
        customer_code=CUSTOMER_CODE,
        SYSLOG_PORT=port,
        TLS_CERT_FILE="cert.pem" if protocol is SonicwallProtocol.TLS else None,
        TLS_KEY_FILE="key.pem" if protocol is SonicwallProtocol.TLS else None,
    )
    pack = provision_service.replace_keywords_in_json_complex(pack, replacements.model_dump())
    return provision_service.convert_port_value_to_int(pack)


# ── The deploy request ──────────────────────────────────────────────


def test_a_request_naming_no_transport_still_deploys_tls():
    """Every deploy was TLS before UDP existed, so a request without a transport keeps getting it."""
    assert request().protocol is SonicwallProtocol.TLS
    # What the deploy form sent before (`tcp_enabled`, never read) changes nothing either.
    assert ProvisionSonicwallRequest(customer_code="x", tcp_enabled=True, hot_data_retention=1, index_replicas=0).protocol is (
        SonicwallProtocol.TLS
    )


def test_each_flag_picks_its_transport():
    assert request(tls_enabled=True).protocol is SonicwallProtocol.TLS
    assert request(udp_enabled=True).protocol is SonicwallProtocol.UDP


def test_both_transports_at_once_is_refused():
    with pytest.raises(ValidationError, match="either TLS or UDP"):
        request(tls_enabled=True, udp_enabled=True)


def test_the_integration_name_is_always_sonicwall():
    assert ProvisionSonicwallRequest(
        customer_code="x",
        integration_name="Fortinet",
        hot_data_retention=1,
        index_replicas=0,
    ).integration_name == ("Sonicwall")


# ── From the request and the connector's keys to the deploy ────────


def test_udp_needs_no_tls_files():
    details = sonicwall_service.build_customer_details(request(udp_enabled=True), CUSTOMER_NAME, keys(port=" 5514 "))

    assert details.protocol_type is SonicwallProtocol.UDP
    assert details.syslog_port == 5514
    assert details.tls_cert_file is None and details.tls_key_file is None
    assert (details.customer_code, details.customer_name, details.hot_data_retention, details.index_replicas) == (
        CUSTOMER_CODE,
        CUSTOMER_NAME,
        30,
        1,
    )


def test_udp_ignores_tls_files_that_are_set():
    details = sonicwall_service.build_customer_details(request(udp_enabled=True), CUSTOMER_NAME, keys(cert="c.pem", key="k.pem"))

    assert details.tls_cert_file is None and details.tls_key_file is None


def test_tls_keeps_its_files():
    details = sonicwall_service.build_customer_details(request(), CUSTOMER_NAME, keys(cert="c.pem", key="k.pem"))

    assert details.protocol_type is SonicwallProtocol.TLS
    assert (details.tls_cert_file, details.tls_key_file) == ("c.pem", "k.pem")


@pytest.mark.parametrize("cert, key", [("", ""), ("c.pem", ""), ("", "k.pem"), ("  ", "k.pem")])
def test_tls_without_its_files_is_refused_before_anything_is_created(cert, key):
    with pytest.raises(HTTPException) as refused:
        sonicwall_service.build_customer_details(request(), CUSTOMER_NAME, keys(cert=cert, key=key))

    assert refused.value.status_code == 400
    assert "TLS_CERT_FILE and TLS_KEY_FILE" in refused.value.detail
    assert "UDP" in refused.value.detail


@pytest.mark.parametrize("port", ["", "abc", "0", "65536", "-1"])
def test_a_syslog_port_that_is_no_port_is_refused(port):
    with pytest.raises(HTTPException) as refused:
        sonicwall_service.build_customer_details(request(udp_enabled=True), CUSTOMER_NAME, keys(port=port))

    assert refused.value.status_code == 400
    assert "SYSLOG_PORT" in refused.value.detail


def test_a_missing_tls_key_reads_as_empty():
    """A connector row without the TLS keys (written outside the form) reads as empty, not as a KeyError."""
    details = sonicwall_service.build_customer_details(request(udp_enabled=True), CUSTOMER_NAME, {"SYSLOG_PORT": "5514"})

    assert details.protocol_type is SonicwallProtocol.UDP


def test_the_route_deploys_udp_with_empty_tls_keys(monkeypatch):
    connector = SimpleNamespace(
        customer_name=CUSTOMER_NAME,
        network_connectors_subscriptions=[
            SimpleNamespace(
                network_connectors_service=SimpleNamespace(service_name="Sonicwall"),
                network_connectors_keys=[SimpleNamespace(auth_key_name=k, auth_value=v) for k, v in keys().items()],
            ),
        ],
    )
    calls = []

    async def customer_connectors(customer_code, session):
        return SimpleNamespace(available_network_connectors=[connector])

    async def find(customer_code, name, response):
        return connector

    async def provision(customer_details, keys, session):
        calls.append((customer_details, keys))
        return sonicwall_routes.ProvisionSonicwallResponse(success=True, message="ok")

    monkeypatch.setattr(sonicwall_routes, "get_customer_network_connectors_by_customer_code", customer_connectors)
    monkeypatch.setattr(sonicwall_routes, "find_customer_network_connector", find)
    monkeypatch.setattr(sonicwall_routes, "provision_sonicwall", provision)

    run(sonicwall_routes.provision_sonicwall_route(request(udp_enabled=True), session=None))

    [(details, sent_keys)] = calls
    assert details.protocol_type is SonicwallProtocol.UDP
    assert details.syslog_port == 5514
    assert sent_keys.TLS_CERT_FILE == ""

    with pytest.raises(HTTPException) as refused:
        run(sonicwall_routes.provision_sonicwall_route(request(), session=None))
    assert refused.value.status_code == 400
    assert len(calls) == 1, "a refused TLS deploy reaches nothing"


# ── Which content packs get installed ──────────────────────────────


SONICWALL_PACKS = [
    "SOCFORTRESS_SONICWALL_INPUT_SYSLOG_TLS",
    "SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP",
    "SOCFORTRESS_SONICWALL_STREAM",
    "SOCFORTRESS_SONICWALL_PROCESSING_PIPELINE",
]


def test_both_sonicwall_inputs_are_available_content_packs():
    assert run(provision_service.retrieve_valid_content_packs("SONICWALL")) == SONICWALL_PACKS


@pytest.mark.parametrize(
    "protocol, expected_input",
    [("TLS", "SOCFORTRESS_SONICWALL_INPUT_SYSLOG_TLS"), ("UDP", "SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP")],
)
def test_only_the_chosen_input_is_installed_with_the_stream_and_pipeline(protocol, expected_input):
    packs = run(provision_service.filter_content_packs(SONICWALL_PACKS, protocol))

    assert packs == [expected_input, "SOCFORTRESS_SONICWALL_STREAM", "SOCFORTRESS_SONICWALL_PROCESSING_PIPELINE"]


def _filter_before_udp_existed(content_packs, protocol_type):
    """`filter_content_packs` as it was, for the callers that existed."""
    if protocol_type == "TCP":
        return [pack for pack in content_packs if "UDP" not in pack]
    if protocol_type == "UDP":
        return [pack for pack in content_packs if "TCP" not in pack]
    return content_packs


@pytest.mark.parametrize(
    "content_pack_type, protocol",
    [
        ("FORTINET", "TCP"),
        ("FORTINET", "UDP"),
        ("CROWDSTRIKE", "TCP"),
        ("BITDEFENDER", "Tcp"),
        ("DEFENDER_FOR_ENDPOINT", "TCP"),
        ("WAZUH", None),
    ],
)
def test_other_connectors_install_what_they_did(content_pack_type, protocol):
    packs = run(provision_service.retrieve_valid_content_packs(content_pack_type))

    assert packs, content_pack_type
    assert run(provision_service.filter_content_packs(packs, protocol)) == _filter_before_udp_existed(packs, protocol)


def test_a_udp_deploy_inserts_the_udp_input_for_the_customer(monkeypatch):
    """The whole content pack path, Graylog faked: what gets inserted and installed, with what names."""
    inserted, installed = [], []

    async def exists(name):
        return False

    async def insert(pack):
        inserted.append(pack)
        return True

    async def install(content_pack_id, revision):
        installed.append((content_pack_id, revision))

    monkeypatch.setattr(provision_service, "does_content_pack_exist", exists)
    monkeypatch.setattr(provision_service, "insert_content_pack", insert)
    monkeypatch.setattr(provision_service, "install_content_pack", install)

    run(
        provision_service.provision_content_pack_network_connector(
            ProvisionNetworkContentPackRequest(
                content_pack_name="SONICWALL",
                keywords=ContentPackKeywords(
                    customer_name=CUSTOMER_NAME,
                    customer_code=CUSTOMER_CODE,
                    protocol_type="UDP",
                    syslog_port=5514,
                ),
            ),
        ),
    )

    assert [pack["name"] for pack in inserted] == [
        sonicwall_service.input_content_pack_name(CUSTOMER_NAME, SonicwallProtocol.UDP),
        f"{CUSTOMER_NAME}_SONICWALL_STREAM",
        "SOCFORTRESS_SONICWALL_PROCESSING_PIPELINE",
    ]
    assert len(installed) == 3
    [udp_input] = inserted[0]["entities"]
    assert values(udp_input["data"]["title"]) == sonicwall_service.input_title(CUSTOMER_NAME, SonicwallProtocol.UDP)
    assert values(udp_input["data"]["configuration"])["port"] == 5514


# ── The templates and the names the service looks them up by ──────


@pytest.mark.parametrize("protocol", list(SonicwallProtocol))
def test_the_service_finds_the_input_by_the_names_the_template_gives_it(protocol):
    pack = installed_template(f"SOCFORTRESS_SONICWALL_INPUT_SYSLOG_{protocol.value}", protocol)
    [entity] = pack["entities"]

    assert pack["name"] == sonicwall_service.input_content_pack_name(CUSTOMER_NAME, protocol)
    assert values(entity["data"]["title"]) == sonicwall_service.input_title(CUSTOMER_NAME, protocol)


@pytest.mark.parametrize("protocol", list(SonicwallProtocol))
def test_no_placeholder_is_left_once_installed(protocol):
    text = json.dumps(installed_template(f"SOCFORTRESS_SONICWALL_INPUT_SYSLOG_{protocol.value}", protocol))

    leftovers = [p for p in PLACEHOLDERS if p in text]
    assert not leftovers, f"left unreplaced: {leftovers}"


def test_the_udp_input_is_a_syslog_udp_input_on_the_customers_port():
    [entity] = installed_template("SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP")["entities"]
    data = values(entity["data"])

    assert data["type"] == "org.graylog2.inputs.syslog.udp.SyslogUDPInput"
    assert data["global"] is True
    assert data["configuration"]["port"] == 5514
    assert isinstance(entity["data"]["configuration"]["port"]["@value"], int), "Graylog rejects a port given as a string"
    assert data["configuration"]["bind_address"] == "0.0.0.0"


def test_both_inputs_land_in_the_customers_stream():
    """The stream matches on static fields; an input without them would send its events nowhere."""
    [stream] = installed_template("SOCFORTRESS_SONICWALL_STREAM")["entities"]
    rules = {(r["field"], r["value"]) for r in values(stream["data"]["stream_rules"])}
    assert values(stream["data"]["matching_type"]) == "AND"

    for protocol in SonicwallProtocol:
        [entity] = installed_template(f"SOCFORTRESS_SONICWALL_INPUT_SYSLOG_{protocol.value}", protocol)["entities"]
        static_fields = values(entity["data"]["static_fields"])
        assert static_fields == {"syslog_type": "sonicwall", "syslog_customer": CUSTOMER_CODE}
        assert rules <= set(static_fields.items()), protocol


def test_the_udp_extractors_run_the_key_value_split_first():
    """The split extractors read `src`, `dst` and `msg`, which the key=value extractor writes.

    Graylog runs an input's extractors by `order`; the Aug 2023 pack gave them all 0 and relied on
    the list order.
    """
    [entity] = installed_template("SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP")["entities"]
    extractors = values(entity["data"]["extractors"])
    [key_value] = [e for e in extractors if [c["type"] for c in e["converters"]] == ["TOKENIZER"]]
    splits = [e for e in extractors if e is not key_value]

    assert key_value["source_field"] == "message"
    assert all(split["order"] > key_value["order"] for split in splits)
    assert {split["target_field"]: (split["source_field"], split["configuration"]["index"]) for split in splits} == {
        "src_ip": ("src", 1),
        "dst_ip": ("dst", 1),
        "msg_cat": ("msg", 1),
        "msg_detail": ("msg", 2),
    }
    assert all(split["type"] == "SPLIT_AND_INDEX" and split["configuration"]["split_by"] == ":" for split in splits)


def test_the_udp_template_is_registered_and_valid_json():
    assert "SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP" in AvailableContentPacks.__members__
    raw = provision_service.get_content_pack_path("SOCFORTRESS_SONICWALL_INPUT_SYSLOG_UDP.json").read_text()
    assert raw.endswith("\n")
    assert not re.search(r"[ \t]+\n", raw), "trailing whitespace fails pre-commit"


# ── The service hands the transport on ─────────────────────────────


def _udp_details():
    return sonicwall_service.build_customer_details(request(udp_enabled=True), CUSTOMER_NAME, keys())


def test_the_content_pack_request_carries_the_transport(monkeypatch):
    sent = []

    async def provision(content_pack_request):
        sent.append(content_pack_request)

    monkeypatch.setattr(sonicwall_service, "provision_content_pack_network_connector", provision)

    run(sonicwall_service.provision_content_pack(_udp_details()))

    [content_pack_request] = sent
    assert content_pack_request.content_pack_name == "SONICWALL"
    assert content_pack_request.keywords.protocol_type == "UDP"
    assert content_pack_request.keywords.tls_cert_file is None


def test_the_udp_input_is_looked_up_by_its_own_names(monkeypatch):
    content_packs, inputs = [], []

    async def stream_id(stream_name):
        return "stream-1"

    async def index_set(request):
        return SimpleNamespace(data=SimpleNamespace(id="index-1"))

    async def content_pack_id(content_pack_name):
        content_packs.append(content_pack_name)
        return f"pack:{content_pack_name}"

    async def input_id(input_name):
        inputs.append(input_name)
        return "input-1"

    async def pipeline_id(subscription):
        return ["pipeline-1"]

    async def meta_attribute(session, customer_code, column_name):
        return 7

    monkeypatch.setattr(sonicwall_service, "get_stream_id_by_stream_name", stream_id)
    monkeypatch.setattr(sonicwall_service, "create_index_set", index_set)
    monkeypatch.setattr(sonicwall_service, "get_content_pack_id_by_content_pack_name", content_pack_id)
    monkeypatch.setattr(sonicwall_service, "get_input_id_by_input_name", input_id)
    monkeypatch.setattr(sonicwall_service, "get_pipeline_id", pipeline_id)
    monkeypatch.setattr(sonicwall_service, "get_customer_meta_attribute", meta_attribute)

    details = _udp_details()
    _, _, stream_pack, input_pack = run(sonicwall_service.get_stream_and_index_ids(details))
    meta = run(sonicwall_service.create_customer_network_connector_meta(details, "stream-1", "index-1", stream_pack, input_pack, None))

    assert content_packs == [f"{CUSTOMER_NAME}_SONICWALL_STREAM", f"{CUSTOMER_NAME}_SONICWALL_INPUT_SYSLOG_UDP"]
    assert inputs == [f"{CUSTOMER_NAME} - SONICWALL FIREWALL LOGS AND EVENTS - UDP"]
    assert meta.graylog_content_pack_input_id == f"pack:{CUSTOMER_NAME}_SONICWALL_INPUT_SYSLOG_UDP"
    assert meta.network_connector_name == "SONICWALL"


# ── The shared level-1 drop rule ────────────────────────────────────

DROP_TITLE = sonicwall_service.LEVEL1_DROP_RULE_TITLE
APP_CONTROL = ("Application Control Detection Alert", "Application Control Prevention Alert")


def test_the_shipped_drop_rule_keeps_ips_and_application_control_alerts():
    """Application Control alerts are level 1 with `fw_action` NA when the firewall only detects: the rule
    dropped them, which emptied every Application Control panel."""
    source = sonicwall_service.shipped_pipeline_rule(DROP_TITLE).source

    assert source.startswith(f'rule "{DROP_TITLE}"')
    assert 'to_long($message.level) == 1 AND $message.fw_action == "NA"' in source
    for kept in ("IPS Detection Alert", *APP_CONTROL):
        assert f'$message.msg_cat != "{kept}"' in source
    assert "drop_message();" in source


def test_the_previous_rule_is_the_shipped_one_without_the_application_control_exceptions():
    shipped = sonicwall_service.shipped_pipeline_rule(DROP_TITLE).source
    without = "\n".join(line for line in shipped.splitlines() if not any(name in line for name in APP_CONTROL))

    assert without == sonicwall_service.LEVEL1_DROP_RULE_PREVIOUS_SOURCES[0]


def rule(source, title=DROP_TITLE, rule_id="rule-1"):
    return PipelineRule(id=rule_id, title=title, description=title, source=source, created_at="2026-01-01T00:00:00.000Z")


def graylog_with(monkeypatch, *rules):
    updates = []

    async def rules_list():
        return PipelineRulesResponse(message="ok", pipeline_rules=list(rules), success=True)

    async def update(rule_id, new_rule):
        updates.append((rule_id, new_rule))

    monkeypatch.setattr(sonicwall_service, "get_pipeline_rules", rules_list)
    monkeypatch.setattr(sonicwall_service, "update_pipeline_rule", update)
    return updates


@pytest.mark.parametrize(
    "stored",
    [
        sonicwall_service.LEVEL1_DROP_RULE_PREVIOUS_SOURCES[0],
        # As some Graylogs hand it back: other line endings and indentation are no edit.
        sonicwall_service.LEVEL1_DROP_RULE_PREVIOUS_SOURCES[0].replace("\n", "\r\n").replace("    ", "\t") + "\n",
    ],
    ids=["as shipped", "reformatted"],
)
def test_a_rule_as_shipped_before_is_updated(monkeypatch, stored):
    updates = graylog_with(monkeypatch, rule(stored), rule('rule "other" when true then end', title="other", rule_id="rule-2"))

    assert run(sonicwall_service.update_level1_drop_rule()) == "updated"

    [(rule_id, new_rule)] = updates
    shipped = sonicwall_service.shipped_pipeline_rule(DROP_TITLE)
    assert rule_id == "rule-1", "only the drop rule is touched"
    assert (new_rule.title, new_rule.description, new_rule.source) == (shipped.title, shipped.description, shipped.source)


def test_a_current_rule_is_left_alone(monkeypatch):
    updates = graylog_with(monkeypatch, rule(sonicwall_service.shipped_pipeline_rule(DROP_TITLE).source))

    assert run(sonicwall_service.update_level1_drop_rule()) == "current"
    assert updates == []


def test_a_rule_edited_in_graylog_is_left_alone(monkeypatch):
    """An operator's own tuning wins: only the exact rule CoPilot shipped before is replaced."""
    edited = sonicwall_service.LEVEL1_DROP_RULE_PREVIOUS_SOURCES[0].replace('"IPS Detection Alert"', '"Something Else"')
    updates = graylog_with(monkeypatch, rule(edited))

    assert run(sonicwall_service.update_level1_drop_rule()) == "edited"
    assert updates == []


def test_no_rule_no_update(monkeypatch):
    updates = graylog_with(monkeypatch, rule('rule "other" when true then end', title="other"))

    assert run(sonicwall_service.update_level1_drop_rule()) == "missing"
    assert updates == []


def _deploy_steps(monkeypatch, update_rule):
    """Fake every external call `provision_sonicwall` makes, recording their order."""
    calls = []

    def step(name, result=None):
        async def fake(*args, **kwargs):
            calls.append(name)
            return result

        return fake

    customer_meta = SimpleNamespace(customer_meta=SimpleNamespace(customer_meta_grafana_org_id="2"))
    meta = SimpleNamespace(grafana_datasource_uid=None, grafana_dashboard_folder_id=None)
    for name, result in {
        "validate_grafana_organization_id": "2",
        "provision_content_pack": None,
        "get_stream_and_index_ids": ("stream-1", "index-1", "pack-stream", "pack-input"),
        "create_customer_network_connector_meta": meta,
        "assign_stream_to_index": None,
        "get_pipeline_id": ["pipeline-1"],
        "connect_stream_to_pipeline": None,
        "create_grafana_datasource": SimpleNamespace(datasource=SimpleNamespace(uid="ds-1")),
        "create_grafana_folder": SimpleNamespace(id=3, uid="folder-1"),
        "get_customer_meta": customer_meta,
        "provision_dashboards": None,
        "insert_into_customer_network_connectors_meta_table": None,
        "set_deployed_flag": None,
    }.items():
        monkeypatch.setattr(sonicwall_service, name, step(name, result))

    async def update():
        calls.append("update_level1_drop_rule")
        return await update_rule()

    monkeypatch.setattr(sonicwall_service, "update_level1_drop_rule", update)
    return calls


def test_a_deploy_updates_the_drop_rule_once_the_pipeline_is_installed(monkeypatch):
    async def updated():
        return "updated"

    calls = _deploy_steps(monkeypatch, updated)

    response = run(sonicwall_service.provision_sonicwall(_udp_details(), keys=None, session=None))

    assert response.success
    assert calls.index("provision_content_pack") < calls.index("update_level1_drop_rule") < calls.index("connect_stream_to_pipeline")


def test_a_failed_rule_update_does_not_fail_the_deploy(monkeypatch):
    async def unreachable():
        raise HTTPException(status_code=500, detail="Failed to collect pipeline rules")

    calls = _deploy_steps(monkeypatch, unreachable)

    response = run(sonicwall_service.provision_sonicwall(_udp_details(), keys=None, session=None))

    assert response.success
    assert calls[-1] == "set_deployed_flag"
