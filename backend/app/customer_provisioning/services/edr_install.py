from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.customer_provisioning.models.default_settings import (
    CustomerProvisioningDefaultSettings,
)
from app.customer_provisioning.schema.edr_install import EDRInstallCommands
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta

# The Linux/macOS installer artifact names are fixed by the repo layout, so they
# are not configurable default-settings columns (unlike the Windows installer filename).
LINUX_INSTALLER_FILENAME = "Client_EDR_install.bash"
MACOS_INSTALLER_FILENAME = "macOS_kickstart.sh"

# Tokens are substituted via str.replace (not str.format) because the PowerShell
# template legitimately contains literal "{" / "}" (e.g. "@{ Authorization = ... }")
# and "$(...)" sequences that would otherwise need escaping.
WINDOWS_TEMPLATE = (
    "$user = '__REPO_USERNAME__'; $pass = '__REPO_PASSWORD__'; "
    '$pair = "$($user):$($pass)"; '
    "$encodedCreds = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($pair)); "
    '$basicAuthValue = "Basic $encodedCreds"; '
    "$Headers = @{ Authorization = $basicAuthValue }; "
    "Invoke-RestMethod -Uri '__REPO_URL__/repository/__REPO_USERNAME__/prod/__WINDOWS_INSTALLER__' "
    '-Headers $Headers -OutFile "$env:TMP\\__WINDOWS_INSTALLER__"; '
    'Start-Process -FilePath "$env:TMP\\__WINDOWS_INSTALLER__" '
    '-ArgumentList \'/q WAZUHMANAGER="__WAZUH_DOMAIN__" WAZUHPASSWORD="__REGISTRATION_PASSWORD__" '
    'CUSTOMERCODE="Windows___CUSTOMER_CODE__" WAZUHREGISTRATIONPORT="__REGISTRATION_PORT__" '
    'WAZUHMANAGERPORT="__LOGS_PORT__"\';'
)

LINUX_TEMPLATE = (
    "if command -v apt >/dev/null 2>&1; then apt update && apt install -y sudo dos2unix; "
    "elif command -v yum >/dev/null 2>&1; then sudo yum install -y dos2unix; "
    'else echo "Error: Neither apt nor yum package manager found."; exit 1; fi; '
    "curl -u __REPO_USERNAME__:__REPO_PASSWORD__ -so ~/__LINUX_INSTALLER__ "
    "__REPO_URL__/repository/__REPO_USERNAME__/installer/__LINUX_INSTALLER__ && "
    "dos2unix ~/__LINUX_INSTALLER__ && "
    "CLIENT_USER=__REPO_USERNAME__ CLIENT_PASS=__REPO_PASSWORD__ bash ~/__LINUX_INSTALLER__ "
    "-i __WAZUH_DOMAIN__ __LOGS_PORT__ __REGISTRATION_PORT__ __REGISTRATION_PASSWORD__ Linux___CUSTOMER_CODE__"
)

# The macOS kickstart script self-configures, so it only needs the repo
# credentials (no Wazuh domain/ports/customer-code arguments).
MACOS_TEMPLATE = (
    "curl -fsSL -u '__REPO_USERNAME__:__REPO_PASSWORD__' "
    "'__REPO_URL__/repository/__REPO_USERNAME__/installer/__MACOS_INSTALLER__' | sudo bash -s -- --no-stagger"
)


async def _get_default_settings(session: AsyncSession) -> CustomerProvisioningDefaultSettings:
    result = await session.execute(select(CustomerProvisioningDefaultSettings))
    settings = result.scalars().first()
    if not settings:
        raise HTTPException(
            status_code=404,
            detail="No customer provisioning default settings found. Configure the EDR repo settings first.",
        )
    return settings


async def _get_customer_meta(customer_code: str, session: AsyncSession) -> CustomersMeta:
    result = await session.execute(
        select(CustomersMeta).filter(CustomersMeta.customer_code == customer_code),
    )
    customer_meta = result.scalars().first()
    if not customer_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Customer meta not found for customer: {customer_code}. Please provision the customer first.",
        )
    return customer_meta


def _require(values: dict) -> None:
    """Raise a single 400 listing every missing prerequisite rather than failing one at a time."""
    missing = [name for name, value in values.items() if value in (None, "")]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate EDR install commands; missing required value(s): {', '.join(missing)}.",
        )


async def generate_edr_install_commands(
    customer_code: str,
    session: AsyncSession,
) -> EDRInstallCommands:
    """
    Render the Windows, Linux and macOS EDR agent install commands for a customer.

    Pulls deployment-wide artifact-repo settings from
    ``customer_provisioning_default_settings`` and per-customer enrollment values
    (registration port, logs port, registration password) from ``customersmeta``.
    Commands are rendered on demand so rotating a password or port never leaves a
    stale command behind.
    """
    logger.info(f"Generating EDR install commands for customer {customer_code}")

    # Confirm the customer exists for a clearer error than a missing-meta 404.
    customer = (await session.execute(select(Customers).filter(Customers.customer_code == customer_code))).scalars().first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer: {customer_code} not found. Please create the customer first.",
        )

    settings = await _get_default_settings(session)
    customer_meta = await _get_customer_meta(customer_code, session)

    _require(
        {
            "repo_url": settings.repo_url,
            "repo_username": settings.repo_username,
            "repo_password": settings.repo_password,
            "windows_edr_installer": settings.windows_edr_installer,
            "wazuh_domain": settings.wazuh_domain,
            "customer_meta_wazuh_registration_port": customer_meta.customer_meta_wazuh_registration_port,
            "customer_meta_wazuh_log_ingestion_port": customer_meta.customer_meta_wazuh_log_ingestion_port,
            "customer_meta_wazuh_auth_password": customer_meta.customer_meta_wazuh_auth_password,
        },
    )

    replacements = {
        "__REPO_URL__": settings.repo_url.rstrip("/"),
        "__REPO_USERNAME__": settings.repo_username,
        "__REPO_PASSWORD__": settings.repo_password,
        "__WINDOWS_INSTALLER__": settings.windows_edr_installer,
        "__LINUX_INSTALLER__": LINUX_INSTALLER_FILENAME,
        "__MACOS_INSTALLER__": MACOS_INSTALLER_FILENAME,
        "__WAZUH_DOMAIN__": settings.wazuh_domain,
        "__REGISTRATION_PASSWORD__": customer_meta.customer_meta_wazuh_auth_password,
        "__REGISTRATION_PORT__": str(customer_meta.customer_meta_wazuh_registration_port),
        "__LOGS_PORT__": str(customer_meta.customer_meta_wazuh_log_ingestion_port),
        "__CUSTOMER_CODE__": customer_code,
    }

    windows = WINDOWS_TEMPLATE
    linux = LINUX_TEMPLATE
    macos = MACOS_TEMPLATE
    for token, value in replacements.items():
        windows = windows.replace(token, value)
        linux = linux.replace(token, value)
        macos = macos.replace(token, value)

    return EDRInstallCommands(windows=windows, linux=linux, macos=macos)
