import os
import pdfkit
from tempfile import NamedTemporaryFile
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader
from fastapi.responses import FileResponse
import platform
from app.data_store.data_store_operations import download_data_store

async def download_template_pdf(template_name: str) -> str:
    """Retrieve the template file content from the data store and save it to a temporary file."""
    template_content = await download_data_store(bucket_name="copilot-case-report-templates", object_name=template_name)
    with NamedTemporaryFile(delete=False, suffix=".html") as tmp_template:
        tmp_template.write(template_content)
        return tmp_template.name

def create_case_context_pdf(case) -> Dict[str, Dict[str, str]]:
    """Prepare the context for the Jinja template."""
    return {
        "case": {
            "name": case.case_name,
            "description": case.case_description,
            "assigned_to": case.assigned_to,
            "case_creation_time": case.case_creation_time,
            "id": case.id,
            "alerts": [
                {
                    "alert_name": alert.alert.alert_name,
                    "alert_description": alert.alert.alert_description,
                    "status": alert.alert.status,
                    "tags": [tag.tag.tag for tag in alert.alert.tags],
                    "assets": [
                        {
                            "asset_name": asset.asset_name,
                            "agent_id": asset.agent_id,
                        }
                        for asset in alert.alert.assets
                    ],
                    "comments": [
                        {
                            "comment": comment.comment,
                            "user_name": comment.user_name,
                            "created_at": comment.created_at,
                        }
                        for comment in alert.alert.comments
                    ],
                    "context": {
                        "source": alert.alert.assets[0].alert_context.source
                        if alert.alert.assets and alert.alert.assets[0].alert_context
                        else None,
                        "context": alert.alert.assets[0].alert_context.context
                        if alert.alert.assets and alert.alert.assets[0].alert_context
                        else None,
                    }
                    if alert.alert.assets
                    else None,
                    "iocs": [
                        {
                            "ioc_value": ioc.ioc.value,
                            "ioc_type": ioc.ioc.type,
                            "ioc_description": ioc.ioc.description,
                        }
                        for ioc in alert.alert.iocs
                    ],
                }
                for alert in case.alerts
            ],
        },
    }

def render_html_template(template_path: str, context: Dict[str, Dict[str, str]]) -> str:
    """Render the Jinja HTML template with the provided context."""
    template_dir = os.path.dirname(template_path)
    template_name = os.path.basename(template_path)

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    rendered_html = template.render(context)

    # Save rendered HTML to a temporary file
    with NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        tmp.write(rendered_html.encode("utf-8"))
        return tmp.name

def convert_html_to_pdf(html_path: str) -> str:
    """Convert the HTML file to a PDF using wkhtmltopdf via pdfkit, with dynamic path detection for different platforms."""
    pdf_path = html_path.replace(".html", ".pdf")
    wkhtmltopdf_paths = []

    # Determine paths to wkhtmltopdf based on the current platform
    try:
        if platform.system() == "Windows":
            # Common installation paths for wkhtmltopdf on Windows
            wkhtmltopdf_paths = [
                r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe"
            ]
        elif platform.system() == "Darwin":  # macOS
            # Common installation paths for wkhtmltopdf on macOS
            wkhtmltopdf_paths = [
                "/usr/local/bin/wkhtmltopdf",
                "/opt/homebrew/bin/wkhtmltopdf"  # For macOS ARM (M1/M2) using Homebrew
            ]
        elif platform.system() == "Linux":
            # Common installation paths for wkhtmltopdf on Linux (Debian-based)
            wkhtmltopdf_paths = [
                "/usr/bin/wkhtmltopdf",
                "/usr/local/bin/wkhtmltopdf"
            ]

        # Try each path until a valid executable is found
        path_to_wkhtmltopdf = None
        for path in wkhtmltopdf_paths:
            try:
                # Check if the executable can be accessed
                config = pdfkit.configuration(wkhtmltopdf=path)
                path_to_wkhtmltopdf = path
                break
            except OSError:
                continue

        # Raise an exception if no valid wkhtmltopdf path is found
        if path_to_wkhtmltopdf is None:
            raise FileNotFoundError("No valid wkhtmltopdf executable found. Ensure wkhtmltopdf is installed and accessible.")

        # Generate the PDF from HTML using the valid wkhtmltopdf path
        pdfkit.from_file(html_path, pdf_path, configuration=config)
    except Exception as e:
        raise RuntimeError(f"Failed to convert HTML to PDF: {str(e)}")

    return pdf_path

def create_file_response_pdf(file_path: str, file_name: Optional[str] = "case_report.pdf") -> FileResponse:
    """Create a FileResponse object for the rendered document."""
    return FileResponse(
        file_path,
        filename=file_name,
        media_type="application/pdf",
    )

def cleanup_temp_files(file_paths: list):
    """Clean up the temporary files."""
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)
