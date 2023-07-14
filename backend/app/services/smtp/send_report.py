import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from app.services.smtp.create_report import create_alerts_report_pdf
from app.services.smtp.universal import EmailTemplate
from app.services.smtp.universal import UniversalEmailCredentials


class EmailReportSender:
    def __init__(self, to_email: str):
        self.to_email = to_email

    def _get_credentials(self) -> dict:
        try:
            return UniversalEmailCredentials.read_all()["emails_configured"][0]
        except IndexError:
            return {"error": "No email credentials found"}

    def create_email_message(self, subject: str, body: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        credentials = self._get_credentials()
        if "error" in credentials:
            return credentials
        msg["From"] = credentials["email"]
        msg["To"] = self.to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))
        return msg

    def attach_pdfs(self, msg: MIMEMultipart, filenames: List[str]) -> MIMEMultipart:
        for filename in filenames:
            with open(filename, "rb") as attachment_file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_file.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                msg.attach(part)
        return msg

    def send_email_with_pdf(self):
        # Generate the PDF report
        create_alerts_report_pdf()

        # Render the email body
        template = EmailTemplate("email_template")
        body = template.render_html_body(template_name="email_template")

        # Create the email message and attach the PDF
        msg = self.create_email_message("Test Report", body)
        if isinstance(msg, dict) and "error" in msg:
            return {"message": msg["error"], "success": False}
        msg = self.attach_pdfs(msg, ["alerts_report.pdf"])

        credentials = self._get_credentials()
        if "error" in credentials:
            return {"message": credentials["error"], "success": False}

        # Send the email
        with smtplib.SMTP(credentials["smtp_server"], credentials["smtp_port"]) as server:
            server.starttls()
            server.login(credentials["email"], credentials["password"])
            text = msg.as_string()
            server.sendmail(credentials["email"], self.to_email, text)

        return {"message": "Report sent successfully", "success": True}
