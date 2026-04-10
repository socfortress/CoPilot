from pydantic import BaseModel


class CustomerDashboardStatsResponse(BaseModel):
    total_alerts: int
    total_cases: int
    total_agents: int
    success: bool
    message: str
