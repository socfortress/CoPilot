from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.services.WazuhIndexer.alerts import AlertsService


def create_pdf():
    service = AlertsService()
    alerts = service.collect_alerts()
    alerts_by_host_percentage = service.get_alerts_by_host_percentage(alerts["alerts_summary"])
    logger.info(alerts_by_host_percentage)
    alerts_by_host_per_index = service.get_alerts_by_host_percentage_by_index_name(alerts["alerts_summary"])
    logger.info(alerts_by_host_per_index)
    c = canvas.Canvas("report.pdf", pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 24)
    c.drawString(30, height - 50, "Test")
    c.save()
