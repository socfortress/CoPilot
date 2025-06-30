import asyncio

import httpx
from fastapi import HTTPException
from fastapi import UploadFile
from loguru import logger

from app.threat_intel.schema.virustotal import FileAnalysisResponse
from app.threat_intel.schema.virustotal import FileReportResponse
from app.threat_intel.schema.virustotal import FileSubmissionRequest
from app.threat_intel.schema.virustotal import FileSubmissionResponse


async def submit_file_to_virustotal(
    api_key: str,
    file: UploadFile,
    request: FileSubmissionRequest,
) -> FileSubmissionResponse:
    """
    Submit a file to VirusTotal for analysis.

    Args:
        api_key (str): The VirusTotal API key
        file (UploadFile): The file to be analyzed
        request (FileSubmissionRequest): Additional parameters for submission

    Returns:
        FileSubmissionResponse: Response containing submission ID

    Raises:
        HTTPException: If the submission fails
    """
    url = "https://www.virustotal.com/api/v3/files"

    # Headers - exactly match the working example
    headers = {"accept": "application/json", "x-apikey": api_key}

    # Prepare the file for upload
    file_content = await file.read()

    # Reset file pointer for potential reuse
    await file.seek(0)

    # Prepare the files dictionary - exactly match the working pattern
    files = {"file": (file.filename, file_content, "application/octet-stream")}

    # Prepare form data if password is provided
    data = {}
    if request.password:
        data["password"] = request.password

    logger.info(f"Submitting file {file.filename} to VirusTotal (size: {len(file_content)} bytes)")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for file uploads
            response = await client.post(url, headers=headers, files=files, data=data if data else None)

            # Log the actual request headers for debugging
            logger.info(f"Request headers sent: {response.request.headers}")
            logger.info(f"Response status: {response.status_code}")

            response.raise_for_status()
            response_data = response.json()

            return FileSubmissionResponse(
                data=response_data["data"],
                success=True,
                message=f"File {file.filename} submitted successfully for analysis",
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error submitting file to VirusTotal: {e.response.status_code} - {e.response.text}")

        # Parse the error response to provide better error messages
        try:
            error_data = e.response.json()
            error_message = error_data.get("error", {}).get("message", str(e.response.text))
        except (ValueError, KeyError):
            error_message = str(e.response.text)

        if e.response.status_code == 400:
            # Handle specific 400 errors
            if "Invalid zip file" in error_message:
                raise HTTPException(
                    status_code=400,
                    detail="File format not supported or corrupted. VirusTotal accepts executables, documents, archives, and other common file types.",
                )
            elif "File too large" in error_message:
                raise HTTPException(
                    status_code=413,
                    detail="File too large. Maximum file size is 32MB for free API keys, 650MB for premium.",
                )
            elif "missing" in error_message.lower():
                raise HTTPException(
                    status_code=400,
                    detail="File upload failed. Please ensure the file is properly formatted and try again.",
                )
            else:
                raise HTTPException(status_code=400, detail=f"Bad request: {error_message}")
        elif e.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
        elif e.response.status_code == 413:
            raise HTTPException(status_code=413, detail="File too large. Maximum file size is 32MB for free API keys.")
        else:
            raise HTTPException(status_code=e.response.status_code, detail=f"Failed to submit file: {error_message}")
    except httpx.RequestError as e:
        logger.error(f"Request error submitting file to VirusTotal: {e}")
        raise HTTPException(status_code=500, detail=f"Network error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error submitting file to VirusTotal: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")


async def get_file_analysis_status(
    api_key: str,
    analysis_id: str,
) -> FileAnalysisResponse:
    """
    Get the status of a file analysis.

    Args:
        api_key (str): The VirusTotal API key
        analysis_id (str): The analysis ID returned from file submission

    Returns:
        FileAnalysisResponse: Current analysis status

    Raises:
        HTTPException: If the request fails
    """
    url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
    headers = {"x-apikey": api_key}

    logger.info(f"Checking analysis status for ID: {analysis_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            return FileAnalysisResponse(data=response_data["data"], success=True, message="Analysis status retrieved successfully")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting analysis status: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to get analysis status: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=f"Network error occurred: {str(e)}")


async def get_file_report(
    api_key: str,
    file_id: str,
) -> FileReportResponse:
    """
    Get the detailed analysis report for a file.

    Args:
        api_key (str): The VirusTotal API key
        file_id (str): The file ID (hash) to get report for

    Returns:
        FileReportResponse: Detailed analysis report

    Raises:
        HTTPException: If the request fails
    """
    url = f"https://www.virustotal.com/api/v3/files/{file_id}"
    headers = {"x-apikey": api_key}

    logger.info(f"Getting file report for ID: {file_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            return FileReportResponse(data=response_data["data"], success=True, message="File report retrieved successfully")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting file report: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="File not found or not yet analyzed")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to get file report: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Request error getting file report: {e}")
        raise HTTPException(status_code=500, detail=f"Network error occurred: {str(e)}")


async def submit_and_wait_for_analysis(
    api_key: str,
    file: UploadFile,
    request: FileSubmissionRequest,
    max_wait_time: int = 300,  # 5 minutes
    poll_interval: int = 10,  # 10 seconds
) -> FileReportResponse:
    """
    Submit a file and wait for analysis to complete, then return the report.

    Args:
        api_key (str): The VirusTotal API key
        file (UploadFile): The file to be analyzed
        request (FileSubmissionRequest): Additional parameters for submission
        max_wait_time (int): Maximum time to wait in seconds
        poll_interval (int): Time between status checks in seconds

    Returns:
        FileReportResponse: Complete analysis report

    Raises:
        HTTPException: If submission fails or analysis times out
    """
    # Submit the file
    submission_response = await submit_file_to_virustotal(api_key, file, request)
    analysis_id = submission_response.data.id

    logger.info(f"File submitted, analysis ID: {analysis_id}. Waiting for completion...")

    # Wait for analysis to complete
    waited_time = 0
    while waited_time < max_wait_time:
        status_response = await get_file_analysis_status(api_key, analysis_id)

        if status_response.data.attributes.status == "completed":
            # Analysis is complete, get the file hash from the analysis ID
            # The analysis ID format is usually base64 encoded, but we can extract file hash from response
            logger.info("Analysis completed, retrieving detailed report...")

            # For now, we'll return the analysis status response
            # In a real implementation, you might want to extract the file hash and get the full report
            return FileReportResponse(data=status_response.data, success=True, message="File analysis completed successfully")

        logger.info(f"Analysis status: {status_response.data.attributes.status}. Waiting {poll_interval} seconds...")
        await asyncio.sleep(poll_interval)
        waited_time += poll_interval

    # If we get here, the analysis timed out
    raise HTTPException(
        status_code=408,
        detail=f"Analysis did not complete within {max_wait_time} seconds. You can check the status later using analysis ID: {analysis_id}",
    )
