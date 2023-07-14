import matplotlib
from loguru import logger
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

matplotlib.use(
    "Agg",
)  # set the backend to Agg which is a non-interactive backend suitable for
# scripts and web servers. This should resolve the main thread is not in main
# loop issue as it bypasses the need for tkinter.
import matplotlib.pyplot as plt

from app.services.WazuhIndexer.alerts import AlertsService


def create_bar_chart(alerts_by_host: dict) -> None:
    """
    Creates a horizontal bar chart with hostnames on the y-axis and the number of alerts on the x-axis.

    Args:
        alerts_by_host (dict): A dictionary containing hostnames and the corresponding number of alerts.

    Returns:
        None
    """
    hostnames = [alert["hostname"] for alert in alerts_by_host["alerts_by_host"]]
    num_alerts = [alert["number_of_alerts"] for alert in alerts_by_host["alerts_by_host"]]

    plt.figure(figsize=(10, 6))  # Set the figure size
    plt.barh(hostnames, num_alerts, color="blue")  # Create a horizontal bar chart
    plt.xlabel("Number of Alerts")  # Label x-axis
    plt.ylabel("Hostnames")  # Label y-axis
    plt.title("Number of Alerts by Host")  # Title of the chart
    plt.tight_layout()
    plt.savefig("alerts_by_host.png")  # Save the figure as a .png file


def create_pdf() -> None:
    """
    Creates a PDF file with a title and an image of the bar chart.

    Returns:
        None
    """
    c = canvas.Canvas("report.pdf", pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 24)
    c.drawString(30, height - 50, "Test")
    c.drawImage("alerts_by_host.png", 50, height / 2, width=400, height=300)  # Draw the image in the canvas
    c.save()


def create_alerts_by_host_pdf() -> None:
    """
    Creates a PDF report of alerts per host.

    This function fetches the alerts per host from the AlertsService, generates a bar chart image using the fetched data,
    and finally creates a PDF file with the generated image.

    Returns:
        None
    """
    service = AlertsService()
    alerts_by_host = service.collect_alerts_by_host()
    logger.info(alerts_by_host)

    create_bar_chart(alerts_by_host)
    create_pdf()
