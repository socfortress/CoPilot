from pydantic import BaseModel, Field


class GenerateReportRequest(BaseModel):
    urls: list[str] = Field(
        [
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/huntress-summary?orgId=1&from=1708725633941&to=1709330433941&panelId=5',
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/huntress-summary?orgId=1&from=1708725654862&to=1709330454862&panelId=1',
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/a1891b09-fba9-498e-807e-1ad774c8557f/sap-users-auth?orgId=44&from=1709303384274&to=1709389784274&panelId=43',
            'http://ashdevcopilot01.socfortress.local:3000/d-solo/ab9bab2c-5d86-43e7-bac2-c1d68fc91342/huntress-summary?orgId=1&from=1706799780600&to=1709391780600&panelId=10'
        ],
        description="List of URLs to generate screenshots for",
    )
