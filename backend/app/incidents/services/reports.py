from typing import Dict
from fastapi.responses import FileResponse
from tempfile import NamedTemporaryFile
import os
from docxtpl import DocxTemplate
from typing import Optional
from app.data_store.data_store_operations import download_data_store
from loguru import logger

async def download_template(template_name: str) -> bytes:
    """Retrieve the template file content from the data store."""
    return await download_data_store(bucket_name="copilot-case-report-templates", object_name=template_name)
# ! TODO: Make this more modular ! #
def create_case_context(case) -> Dict[str, Dict[str, str]]:
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
                        "source": alert.alert.assets[0].alert_context.source if alert.alert.assets and alert.alert.assets[0].alert_context else None,
                        "context": alert.alert.assets[0].alert_context.context if alert.alert.assets and alert.alert.assets[0].alert_context else None,
                    } if alert.alert.assets else None
                }
                for alert in case.alerts
            ]
        }
    }



def save_template_to_tempfile(template_file_content: bytes) -> str:
    """Save the template content to a temporary file."""
    with NamedTemporaryFile(delete=False, suffix=".docx") as tmp_template:
        tmp_template.write(template_file_content)
        return tmp_template.name

def render_document_with_context(template_path: str, context: Dict[str, Dict[str, str]]) -> str:
    """Load and render the document template with the given context."""
    doc = DocxTemplate(template_path)
    doc.render(context)
    with NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        doc.save(tmp.name)
        return tmp.name

def create_file_response(file_path: str, file_name: Optional[str] = "case_report.docx") -> FileResponse:
    """Create a FileResponse object for the rendered document."""
    return FileResponse(
        file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

def cleanup_temp_files(file_paths: list):
    """Clean up the temporary files."""
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)
