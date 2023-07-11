from flask import Blueprint
from flask import request

from app.services.DFIR_IRIS.alerts import AlertsService
from app.services.DFIR_IRIS.assets import AssetsService
from app.services.DFIR_IRIS.cases import CasesService
from app.services.DFIR_IRIS.notes import NotesService

bp = Blueprint("dfir_iris", __name__)


@bp.route("/dfir_iris/cases", methods=["GET"])
def get_cases():
    """
    Endpoint to retrieve all the cases from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of cases.
    """
    service = CasesService()
    cases = service.list_cases()
    return cases


@bp.route("/dfir_iris/cases/<case_id>", methods=["GET"])
def get_case(case_id: str):
    """
    Endpoint to retrieve a specific case from DFIR IRIS.

    Args:
        case_id (str): The ID of the case to retrieve.

    Returns:
        json: A JSON response containing the case data.
    """
    service = CasesService()
    case = service.get_case(case_id=case_id)
    return case


@bp.route("/dfir_iris/cases/<case_id>/notes", methods=["GET"])
def get_case_notes(case_id: int):
    """
    Endpoint to retrieve notes of a specific case from DFIR IRIS.

    Args:
        case_id (str): The ID of the case to retrieve notes from.

    Returns:
        json: A JSON response containing the list of notes for the case.
    """
    notes_service = NotesService()
    notes = notes_service.get_case_notes(search_term="%", cid=case_id)
    return notes


@bp.route("/dfir_iris/cases/<case_id>/note", methods=["POST"])
def create_case_note(case_id: str):
    """
    Endpoint to create a note for a specific case in DFIR IRIS.

    Args:
        case_id (str): The ID of the case to create a note for.

    Returns:
        json: A JSON response containing the result of the note creation operation.
    """
    note_title = request.json["note_title"]
    note_content = request.json["note_content"]
    notes_service = NotesService()
    created_note = notes_service.create_case_note(
        cid=case_id,
        note_title=note_title,
        note_content=note_content,
    )
    return created_note


@bp.route("/dfir_iris/cases/<case_id>/assets", methods=["GET"])
def get_case_assets(case_id: str):
    """
    Endpoint to retrieve assets of a specific case from DFIR IRIS.

    Args:
        case_id (str): The ID of the case to retrieve assets from.

    Returns:
        json: A JSON response containing the list of assets for the case.
    """
    asset_service = AssetsService()
    assets = asset_service.get_case_assets(cid=case_id)
    return assets


@bp.route("/dfir_iris/alerts", methods=["GET"])
def get_alerts():
    """
    Endpoint to retrieve all alerts from DFIR IRIS.

    Returns:
        json: A JSON response containing the list of alerts.
    """
    service = AlertsService()
    alerts = service.list_alerts()
    return alerts
