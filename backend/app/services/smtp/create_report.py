from typing import List

import matplotlib
from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

matplotlib.use(
    "Agg",
)  # set the backend to Agg which is a non-interactive backend suitable
# for scripts and web servers. This should resolve the main thread is not
# in main loop issue as it bypasses the need for tkinter.
import matplotlib.pyplot as plt

from app.services.WazuhIndexer.alerts import AlertsService


def fetch_alert_data(service, fetch_func):
    alerts = fetch_func()
    logger.info(alerts)
    return alerts


def create_bar_chart(alerts: dict, title: str, output_filename: str) -> None:
    entities = [alert["hostname"] for alert in alerts["alerts_by_host"]]
    num_alerts = [alert["number_of_alerts"] for alert in alerts["alerts_by_host"]]

    plt.figure(figsize=(10, 6))
    plt.barh(entities, num_alerts, color="blue")
    plt.xlabel("Number of Alerts")
    plt.ylabel("Hostnames")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_filename)


def create_pie_chart(alerts: dict, title: str, output_filename: str) -> None:
    entities = [alert["rule"] for alert in alerts["alerts_by_rule"]]
    num_alerts = [alert["number_of_alerts"] for alert in alerts["alerts_by_rule"]]

    plt.figure(figsize=(10, 6))
    plt.pie(num_alerts, labels=entities, autopct="%1.1f%%")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_filename)


def create_pdf(title: str, image_filenames: List[str], pdf_filename: str) -> None:
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 24)
    c.drawString(30, height - 50, title)

    image_height = height / 2
    for i, image_filename in enumerate(image_filenames):
        c.drawImage(image_filename, 50, image_height - i * 300, width=400, height=300)
    c.save()


def create_alerts_report_pdf() -> None:
    service = AlertsService()

    alerts_by_host = fetch_alert_data(service, service.collect_alerts_by_host)
    create_bar_chart(alerts_by_host, "Number of Alerts by Host", "alerts_by_host.png")

    alerts_by_rules = fetch_alert_data(service, service.collect_alerts_by_rule)
    create_pie_chart(alerts_by_rules, "Number of Alerts by Rule", "alerts_by_rule.png")

    create_pdf("Test", ["alerts_by_host.png", "alerts_by_rule.png"], "alerts_report.pdf")
