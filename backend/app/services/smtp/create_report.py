# from app.services.WazuhIndexer.alerts import AlertsService
# from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_pdf():
    # service = AlertsService()
    # alerts = service.collect_alerts()
    # logger.info(alerts)
    c = canvas.Canvas("report.pdf", pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 24)
    c.drawString(30, height - 50, "Test")
    c.save()
