from pydantic import BaseModel
from pydantic import Field


class EDRInstallCommands(BaseModel):
    windows: str = Field(
        ...,
        description="PowerShell one-liner that downloads and silently installs the Windows EDR agent.",
    )
    linux: str = Field(
        ...,
        description="Bash one-liner that downloads and runs the Linux EDR agent installer.",
    )
    macos: str = Field(
        ...,
        description="Bash one-liner that downloads and runs the macOS EDR agent kickstart installer.",
    )


class EDRInstallCommandsResponse(BaseModel):
    message: str = Field(
        ...,
        examples=["EDR install commands generated successfully"],
        description="Message indicating the result of the operation",
    )
    success: bool = Field(
        ...,
        examples=[True],
        description="Whether the EDR install commands were generated successfully or not",
    )
    customer_code: str = Field(
        ...,
        examples=["CUST123"],
        description="The customer code the commands were generated for",
    )
    commands: EDRInstallCommands = Field(
        ...,
        description="The generated Windows and Linux EDR agent install commands",
    )
