import urllib.request
from typing import List

import matplotlib
from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# from reportlab.pdfgen import canvas
from reportlab.platypus import Image
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate
from reportlab.platypus import Spacer

matplotlib.use(
    "Agg",
)  # set the backend to Agg which is a non-interactive backend suitable
# for scripts and web servers. This should resolve the main thread is not
# in main loop issue as it bypasses the need for tkinter.
import matplotlib.pyplot as plt

from app.services.wazuh_indexer.alerts import AlertsService

# ! TODO: Just a template


def fetch_alert_data(service, fetch_func):
    """
    Fetches alert data using the provided function.

    Args:
        service: An instance of the service to use for fetching data.
        fetch_func (function): The function to use to fetch the data.

    Returns:
        Returns the result of the fetch function.
    """
    alerts = fetch_func()
    logger.info(alerts)
    return alerts


def create_bar_chart(alerts: dict, title: str, output_filename: str) -> None:
    """
    Creates a horizontal bar chart of alerts and saves it to a file.

    Args:
        alerts (dict): A dictionary containing alert data.
        title (str): The title for the chart.
        output_filename (str): The filename to save the chart to.

    Returns:
        None
    """
    entities = [alert["hostname"] for alert in alerts["alerts_by_host"]]
    num_alerts = [alert["number_of_alerts"] for alert in alerts["alerts_by_host"]]

    plt.figure(figsize=(10, 10))
    plt.barh(entities, num_alerts, color="blue")
    plt.xlabel("Number of Alerts")
    plt.ylabel("Hostnames")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_filename)


def create_pie_chart(alerts: dict, title: str, output_filename: str) -> None:
    """
    Creates a pie chart of alerts and saves it to a file.

    Args:
        alerts (dict): A dictionary containing alert data.
        title (str): The title for the chart.
        output_filename (str): The filename to save the chart to.

    Returns:
        None
    """
    entities = [alert["rule"] for alert in alerts["alerts_by_rule"]]
    num_alerts = [alert["number_of_alerts"] for alert in alerts["alerts_by_rule"]]

    plt.figure(figsize=(10, 6))
    plt.pie(num_alerts, labels=entities, autopct="%1.1f%%")
    plt.legend(
        entities,
        loc="lower right",
        bbox_to_anchor=(1.0, 1.0),
    )  # Add this line to include a legend
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_filename)


def create_pdf(title: str, image_filenames: List[str], pdf_filename: str) -> None:
    """
    Creates a PDF containing images.

    Args:
        title (str): The title for the PDF.
        image_filenames (List[str]): A list of image filenames to include in the PDF.
        pdf_filename (str): The filename to save the PDF to.

    Returns:
        None
    """
    # Download the SOC Fortress logo
    logo_url = "https://socfortress-images.s3.amazonaws.com/socfortress_logo_orange.png"
    logo_filename = "socfortress_logo_orange.png"
    urllib.request.urlretrieve(logo_url, logo_filename)

    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []

    # Add a cover page
    Story.append(Spacer(1, 2 * inch))
    Story.append(Image(logo_filename, 5 * inch, 5 * inch))  # Adjust size as needed
    Story.append(Spacer(1, 1 * inch))
    style = styles["Title"]
    Story.append(Paragraph(title, style))
    Story.append(Spacer(1, 2 * inch))

    # Add the images
    for i, image_filename in enumerate(image_filenames):
        Story.append(Image(image_filename, 6 * inch, 4 * inch))  # Adjust size as needed
        Story.append(Spacer(1, 0.2 * inch))

    doc.build(Story)


def create_alerts_report_pdf() -> None:
    """
    Creates a PDF report of alerts including a bar chart and a pie chart.

    Returns:
        None
    """
    service = AlertsService()

    alerts_by_host = fetch_alert_data(service, service.collect_alerts_by_host)
    create_bar_chart(alerts_by_host, "Number of Alerts by Host", "alerts_by_host.png")

    alerts_by_rules = fetch_alert_data(service, service.collect_alerts_by_rule)
    create_pie_chart(alerts_by_rules, "Number of Alerts by Rule", "alerts_by_rule.png")

    create_pdf(
        "Test",
        ["alerts_by_host.png", "alerts_by_rule.png"],
        "alerts_report.pdf",
    )
