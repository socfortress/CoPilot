"""Whether cloud scans can run here, for the UI to say so before anyone fills a form (#1328)."""

from app.cloud_assessment.schema.cloud_assessment import AvailabilityResponse
from app.cloud_assessment.services.crypto import key_configured
from app.cloud_assessment.services.runner_client import RunnerClient
from app.cloud_assessment.services.runner_client import RunnerError


async def availability() -> AvailabilityResponse:
    """The encryption key, the runner's settings, and copilot-prowler's answer to ``/v1/health``.
    A runner that can't be asked is named by a fixed text, never by its address or answer."""
    answer = AvailabilityResponse(
        success=True,
        message="Cloud assessment availability",
        encryption_key_configured=key_configured(),
        runner_configured=False,
        runner_reachable=False,
    )
    async with RunnerClient.from_env() as runner:
        problem = runner.problem()
        if problem:
            answer.runner_problem = RunnerError(problem).message
            return answer
        answer.runner_configured = True
        try:
            health = await runner.health()
        except RunnerError as error:
            answer.runner_problem = error.message
            return answer
    answer.runner_reachable = True
    answer.runner_version = health["runner_version"]
    answer.prowler_version = health["prowler_version"]
    answer.powershell = health["powershell"]
    answer.providers = health["providers"]
    return answer
