import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from app.services.smtp.universal import UniversalEmailCredentials, EmailTemplate  # add EmailTemplate to the import
from app.services.smtp.create_report import create_pdf

def send_email_with_pdf():
    # Generate the PDF report
    create_pdf()

    try:
        credentials = UniversalEmailCredentials.read_all()['emails_configured'][0]
    except IndexError:
        raise Exception("No email credentials found in the database.")

    msg = MIMEMultipart()
    msg['From'] = credentials['email']
    msg['To'] = 'walton.taylor23@gmail.com'
    msg['Subject'] = 'Test Report'

    # Use EmailTemplate for the email body
    template = EmailTemplate('email_template')  # replace 'email_template' with the name of your template without .jinja
    body = template.render_html_body(template_name="email_template")  # replace this line
    msg.attach(MIMEText(body, 'html'))  # add 'html' as the second argument to MIMEText

    filename = 'report.pdf'
    attachment = open(filename, 'rb')
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= {}".format(filename))
    msg.attach(part)

    server = smtplib.SMTP(credentials['smtp_server'], credentials['smtp_port'])
    server.starttls()
    server.login(credentials['email'], credentials['password'])
    text = msg.as_string()
    server.sendmail(credentials['email'], 'walton.taylor23@gmail.com', text)
    server.quit()

    return {"message": "Report sent successfully", "success": True}

