## SMTP Overview

### <span style="color:blue">EmailCredentials Model</span>

This Python script, `smtp.py`, is centered around creating a SQLAlchemy model for storing email credentials and SMTP settings, and a Marshmallow schema for serializing and deserializing instances of the model.

Here is a detailed breakdown:

## Import Statements

The necessary libraries and modules are imported. These include `datetime` for handling date and time information, various types from `sqlalchemy` for defining database table structure, and the `db` and `ma` instances from the `app` module.

## EmailCredentials Class

This class inherits from SQLAlchemy's `Model` class and represents the `EmailCredentials` table in the database. It has six columns: `id`, `email`, `password`, `smtp_server`, `smtp_port`, and `timestamp`.

-   `id`: This is the primary key of the table. It is an integer.
-   `email`: This column stores the user's email. It is a string of up to 100 characters, and it cannot be null.
-   `password`: This column stores the password of the user's email. It is a string of up to 100 characters, and it cannot be null.
-   `smtp_server`: This column stores the SMTP server address. It is a string of up to 100 characters, and it cannot be null.
-   `smtp_port`: This column stores the SMTP port. It is an integer, and it cannot be null.
-   `timestamp`: This column stores the time when the email credential was created. It is a `DateTime` object and by default, it's set to the time when a new row is created.

The `__init__` method initializes a new instance of the class with `email`, `password`, `smtp_server`, and `smtp_port`. The `__repr__` method returns a string representation of an instance of the class.

## EmailCredentialsSchema Class

This class inherits from Marshmallow's `Schema` class. It is used to serialize and deserialize instances of the `EmailCredentials` class to and from Python dictionaries. This is useful for converting the model instances into a format that can be used in JSON APIs.

The `Meta` class within `EmailCredentialsSchema` specifies the fields to include in the serialized output.

-   `email_credentials_schema` and `email_credentials_schemas`: These are instances of the `EmailCredentialsSchema` class. `email_credentials_schema` is used to serialize a single `EmailCredentials` instance, while `email_credentials_schemas` is used to serialize a list of `EmailCredentials` instances (note the `many=True` argument).

::: app.models.smtp
<br>

### <span style="color:green">SMTP Routes</span>

This Python script, `smtp.py`, uses Flask to create a web server with several endpoints for handling HTTP requests related to SMTP (Simple Mail Transfer Protocol) credentials and sending reports via email.

Here's a detailed description:

## Import Statements

It begins by importing required modules. These include `Blueprint`, `jsonify`, and `request` from Flask for creating a set of routes and handling JSON responses and requests, `logger` from loguru for logging, and `EmailReportSender` and `UniversalEmailCredentials` from `app.services.smtp`.

## Blueprint Creation

It then creates a `Blueprint` named `smtp`. A Blueprint is a way to organize a group of related routes, and it's being used here to create routes for the SMTP-related endpoints.

## Route Definitions

Following this, it defines several routes:

-   `@bp.route("/smtp/credential", methods=["POST"])`: This route responds to HTTP POST requests at the `/smtp/credential` endpoint. It stores SMTP credentials in the `smtp_credentials` table. The endpoint expects a JSON payload with the email, password, SMTP server, and SMTP port. If the payload is valid, it uses `UniversalEmailCredentials.create()` to store the credentials and returns a JSON response indicating whether the storage was successful.

-   `@bp.route("/smtp/credentials", methods=["GET"])`: This route responds to HTTP GET requests at the `/smtp/credentials` endpoint. It retrieves a list of all SMTP credentials from the `smtp_credentials` table using the `UniversalEmailCredentials.read_all()` method and returns them as a JSON response.

-   `@bp.route("/smtp/report", methods=["POST"])`: This route responds to HTTP POST requests at the `/smtp/report` endpoint. It sends a report via email. The endpoint expects a JSON payload with the recipient's email address. If the payload is valid, it uses `EmailReportSender(to_email).send_email_with_pdf()` to send the report and returns a JSON response indicating whether the sending was successful.

## Error Handling

If the payload of the request to store SMTP credentials or send a report is invalid, an error message is logged and returned as a JSON response with a 400 status code.

::: app.routes.smtp
<br>

### <span style="color:red">Create Report Services</span>

This Python script, `create_report.py`, generates a PDF report about alerts with two types of charts (bar and pie) and exports the report to a PDF file. It uses matplotlib for creating charts, reportlab for creating the PDF, and loguru for logging. It fetches the alerts data from an `AlertsService`.

Here's a detailed description:

## Import Statements

It begins by importing required modules. These include `urllib.request` for downloading files, `matplotlib` for creating charts, `loguru` for logging, and `types` from the `typing` module for type annotations. `reportlab` is used to create the PDF.

## Functions

### fetch_alert_data(service, fetch_func)

Fetches alert data using the provided function and logs the data.

### create_bar_chart(alerts: dict, title: str, output_filename: str)

Creates a horizontal bar chart of alerts by host and saves it to a file.

### create_pie_chart(alerts: dict, title: str, output_filename: str)

Creates a pie chart of alerts by rule and saves it to a file.

### create_pdf(title: str, image_filenames: List[str], pdf_filename: str)

Creates a PDF containing images (the bar chart and the pie chart) and the SOC Fortress logo, which is downloaded from a URL. The PDF is saved to a file.

### create_alerts_report_pdf()

This function uses the `AlertsService` to fetch alerts data, then creates a bar chart of alerts by host and a pie chart of alerts by rule. It finally creates a PDF report that includes these charts.

## Matplotlib Backend Setting

The Agg backend of matplotlib is used, which is a non-interactive backend suitable for scripts and web servers. This should resolve the "main thread is not in main loop" issue as it bypasses the need for tkinter.

## Execution of Report Generation

The last line of the script calls the `create_alerts_report_pdf()` function to generate the report when the script is run.

::: app.services.smtp.create_report

### <span style="color:red">Send Report Services</span>

This Python script, `send_report.py`, is designed to send an email report with PDF attachments. It uses the `smtplib` library for sending emails, the `email` library for creating email messages with attachments, and the `create_alerts_report_pdf` function from the `app.services.smtp.create_report` module for generating the PDF report.

Here's a detailed description:

## Import Statements

It begins by importing required modules. These include `smtplib` for the SMTP client session object that can be used to send mail, `email` for managing email messages, and `typing` for type annotations.

## EmailReportSender Class

This class is used to send an email report with PDF attachments. It has the following methods:

-   `__init__(self, to_email: str)`: Constructor for the `EmailReportSender` class. It initializes the class with the recipient's email address.

-   `_get_credentials(self) -> dict`: Fetches the email credentials.

-   `create_email_message(self, subject: str, body: str) -> MIMEMultipart`: Creates an email message with the provided subject and body.

-   `attach_pdfs(self, msg: MIMEMultipart, filenames: List[str]) -> MIMEMultipart`: Attaches PDF files to an email message.

-   `send_email_with_pdf(self)`: Sends an email with a PDF report. It generates the PDF report, creates an email message, attaches the report to the message, and then sends the email. It returns a dictionary containing a message describing the result of the operation and a success indicator.

These methods collectively allow the `EmailReportSender` class to generate a report, create an email message with the report attached, and send the email message. They use helper methods to fetch email credentials, create the email message, attach the PDFs, and send the email.

::: app.services.smtp.send_report

### <span style="color:red">Universal Services</span>

::: app.services.smtp.universal
