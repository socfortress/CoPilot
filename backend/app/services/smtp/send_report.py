import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.smtp.create_report import create_alerts_by_host_pdf
from app.services.smtp.universal import EmailTemplate
from app.services.smtp.universal import UniversalEmailCredentials


def create_email_message(subject: str, from_email: str, to_email: str, body: str) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))
    return msg


def attach_pdf(msg: MIMEMultipart, filename: str) -> MIMEMultipart:
    with open(filename, "rb") as attachment_file:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_file.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {filename}")
        msg.attach(part)
    return msg


def send_email_with_pdf():
    # Generate the PDF report
    create_alerts_by_host_pdf()

    # Get email credentials
    try:
        credentials = UniversalEmailCredentials.read_all()["emails_configured"][0]
    except IndexError:
        raise Exception("No email credentials found in the database.")

    # Render the email body
    template = EmailTemplate("email_template")
    body = template.render_html_body(template_name="email_template")

    # Create the email message and attach the PDF
    msg = create_email_message("Test Report", credentials["email"], "walton.taylor23@gmail.com", body)
    msg = attach_pdf(msg, "report.pdf")

    # Send the email
    with smtplib.SMTP(credentials["smtp_server"], credentials["smtp_port"]) as server:
        server.starttls()
        server.login(credentials["email"], credentials["password"])
        text = msg.as_string()
        server.sendmail(credentials["email"], "walton.taylor23@gmail.com", text)

    return {"message": "Report sent successfully", "success": True}
