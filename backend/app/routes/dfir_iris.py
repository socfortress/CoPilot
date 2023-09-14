from flask import Blueprint
from flask import jsonify
from flask import request

from app.services.dfir_iris.alerts import IRISAlertsService
from app.services.dfir_iris.assets import AssetsService
from app.services.dfir_iris.cases import CasesService
from app.services.dfir_iris.notes import NotesService
from app.services.dfir_iris.users import IRISUsersService

bp = Blueprint("dfir_iris", __name__)


@bp.route("/dfir_iris/cases", methods=["GET"])
def get_cases():
    """
    Handle GET requests at the "/cases" endpoint. Retrieve all cases from DFIR IRIS.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of cases.
    """
    service = CasesService()
    cases = service.list_cases()
    return cases


@bp.route("/dfir_iris/cases/kpi", methods=["GET"])
def get_cases_kpi():
    """
    Handle GET requests at the "/cases" endpoint. Retrieve all cases from DFIR IRIS and calculate their KPI.

    Currently supports collecting cases older than 24 hours that are still open.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of cases.
    """
    service = CasesService()
    result = service.list_cases()

    if not result["success"]:
        return jsonify(result), 500

    cases = service.calculate_kpis(result["cases"])
    return jsonify({"cases": cases}), 200


@bp.route("/dfir_iris/cases/<case_id>", methods=["GET"])
def get_case(case_id: str):
    """
    Handle GET requests at the "/cases/<case_id>" endpoint. Retrieve a specific case from DFIR IRIS.

    Args:
        case_id (str): The ID of the case to retrieve.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the case data.
    """
    service = CasesService()
    case = service.get_case(case_id=case_id)
    return case


@bp.route("/dfir_iris/cases/<case_id>/notes", methods=["GET"])
def get_case_notes(case_id: int):
    """
    Handle GET requests at the "/cases/<case_id>/notes" endpoint. Retrieve notes of a specific case from DFIR IRIS.

    Args:
        case_id (str): The ID of the case to retrieve notes from.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of notes for the case.
    """
    notes_service = NotesService()
    notes = notes_service.get_case_notes(search_term="%", cid=case_id)
    return notes


@bp.route("/dfir_iris/cases/<case_id>/note", methods=["POST"])
def create_case_note(case_id: str):
    """
    Handle POST requests at the "/cases/<case_id>/note" endpoint. Create a note for a specific case in DFIR IRIS.

    Args:
        case_id (str): The ID of the case to create a note for.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the result of the note creation operation.
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
    Handle GET requests at the "/cases/<case_id>/assets" endpoint. Retrieve assets of a specific case from DFIR IRIS.

    Args:
        case_id (str): The ID of the case to retrieve assets from.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of assets for the case.
    """
    asset_service = AssetsService()
    assets = asset_service.get_case_assets(cid=case_id)
    return assets


@bp.route("/dfir_iris/alerts", methods=["GET"])
def get_alerts():
    """
    Handle GET requests at the "/alerts" endpoint. Retrieve all alerts from DFIR IRIS.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of alerts.
    """
    service = IRISAlertsService()
    alerts = service.list_alerts()
    return alerts


@bp.route("/dfir_iris/alerts/bookmark/<alert_id>", methods=["POST"])
def bookmark_alert(alert_id: str):
    """
    Handle POST requests at the "/alerts/<alert_id>/bookmark" endpoint. Bookmark an alert in DFIR IRIS.

    Args:
        alert_id (str): The ID of the alert to bookmark.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the result of the bookmark operation.
    """
    service = IRISAlertsService()
    bookmarked_alert = service.bookmark_alert(alert_id=alert_id)
    return bookmarked_alert


@bp.route("/dfir_iris/alerts/unbookmark/<alert_id>", methods=["POST"])
def unbookmark_alert(alert_id: str):
    """
    Handle POST requests at the "/alerts/<alert_id>/unbookmark" endpoint. Unbookmark an alert in DFIR IRIS.

    Args:
        alert_id (str): The ID of the alert to unbookmark.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the result of the unbookmark operation.
    """
    service = IRISAlertsService()
    unbookmarked_alert = service.unbookmark_alert(alert_id=alert_id)
    return unbookmarked_alert


@bp.route("/dfir_iris/alerts/bookmarked", methods=["GET"])
def get_bookmarked_alerts():
    """
    Handle GET requests at the "/alerts/bookmarked" endpoint. Retrieve all bookmarked alerts from DFIR IRIS.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of bookmarked alerts.
    """
    service = IRISAlertsService()
    alerts = service.list_bookmarked_alerts()
    return alerts


@bp.route("/dfir_iris/users", methods=["GET"])
def get_users():
    """
    Handle GET requests at the "/users" endpoint. Retrieve all users from DFIR IRIS.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the list of users.
    """
    service = IRISUsersService()
    users = service.list_users()
    return users


@bp.route("/dfir_iris/users/assign/<alert_id>", methods=["POST"])
def assign_user_to_alert(alert_id: str):
    """
    Handle POST requests at the "/alerts/<alert_id>/assign" endpoint. Assign a user to an alert in DFIR IRIS.

    Args:
        alert_id (str): The ID of the alert to assign a user to.

    Returns:
        Response: A Flask Response object carrying a JSON representation of the result of the user assignment operation.
    """
    alert_owner_id = request.json["alert_owner_id"]
    service = IRISUsersService()
    assigned_user = service.assign_user_alert(alert_id=alert_id, alert_owner_id=alert_owner_id)
    return assigned_user
