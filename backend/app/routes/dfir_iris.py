from flask import Blueprint
from flask import request

from app.services.DFIR_IRIS.alerts import AlertsService
from app.services.DFIR_IRIS.assets import AssetsService
from app.services.DFIR_IRIS.cases import CasesService
from app.services.DFIR_IRIS.notes import NotesService

# from loguru import logger


bp = Blueprint("dfir_iris", __name__)


@bp.route("/dfir_iris/cases", methods=["GET"])
def get_cases():
    """
    Endpoint to collect cases from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    service = CasesService()
    cases = service.list_cases()
    return cases


@bp.route("/dfir_iris/cases/<case_id>", methods=["GET"])
def get_case(case_id):
    """
    Endpoint to collect a specific case from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    # Get the Case ID from the URL
    service = CasesService()
    case_id_exists = service.check_case_id(case_id=case_id)
    if case_id_exists["success"] is False:
        return case_id_exists
    case = service.get_case(case_id=case_id)
    return case


@bp.route("/dfir_iris/cases/<case_id>/notes", methods=["GET"])
def get_case_notes(case_id):
    """
    Endpoint to collect notes from a specific case from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    # Get the Case ID from the URL
    case_service = CasesService()
    notes_service = NotesService()
    search_term = "%"
    case_id_exists = case_service.check_case_id(case_id=case_id)
    if case_id_exists["success"] is False:
        return case_id_exists
    notes = notes_service.get_case_notes(search_term=search_term, cid=int(case_id))
    return notes


@bp.route("/dfir_iris/cases/<case_id>/note", methods=["POST"])
def create_case_note(case_id):
    """
    Endpoint to create notes from a specific case from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    # Get the Case ID from the URL
    note_title = request.json["note_title"]
    note_content = request.json["note_content"]
    case_service = CasesService()
    notes_service = NotesService()
    case_id_exists = case_service.check_case_id(case_id=case_id)
    if case_id_exists["success"] is False:
        return case_id_exists
    created_note = notes_service.create_case_note(
        cid=int(case_id),
        note_title=note_title,
        note_content=note_content,
    )
    return created_note


@bp.route("/dfir_iris/cases/<case_id>/assets", methods=["GET"])
def get_case_assets(case_id):
    """
    Endpoint to collect assets from a specific case from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    asset_service = AssetsService()
    case_service = CasesService()

    case_id_exists = case_service.check_case_id(case_id=case_id)
    if case_id_exists["success"] is False:
        return case_id_exists
    assets = asset_service.get_case_assets(cid=int(case_id))
    return assets


@bp.route("/dfir_iris/alerts", methods=["GET"])
def get_alerts():
    """
    Endpoint to collect alerts from DFIR-IRIS

    Returns:
        json: A JSON response containing the list of all the messages.
    """
    service = AlertsService()
    alerts = service.list_alerts()
    return alerts
