import dnstwist
from loguru import logger

from app.integrations.dnstwist.schema.analyze import DomainAnalysisResponse
from app.integrations.dnstwist.schema.analyze import DomainRequestBody


def analyze_domain(domain: DomainRequestBody) -> DomainAnalysisResponse:
    """
    Analyze the domain using dnstwist and return the results for registered domains.

    Args:
        domain (DomainRequestBody): The domain to analyze.

    Returns:
        DomainAnalysisResponse: The response from DNS Twist.
    """
    logger.info(f"Analyzing domain {domain} with DNS Twist.")
    logger.info("Analyzing domain for registered domains.")
    data = dnstwist.run(domain=domain, registered=True, format="json")
    return DomainAnalysisResponse(
        data=data,
        message="Domain analysis completed.",
        success=True,
    )


def analyze_domain_phishing(domain: DomainRequestBody) -> DomainAnalysisResponse:
    """
    Analyze the domain using dnstwist and return the results for registered domains.

    Args:
        domain (DomainRequestBody): The domain to analyze.

    Returns:
        DomainAnalysisResponse: The response from DNS Twist.
    """
    logger.info(f"Analyzing domain {domain} with DNS Twist.")
    logger.info("Analyzing domain for registered domains.")
    data = dnstwist.run(
        domain=domain,
        registered=True,
        format="json",
        lsh=True,
    )
    return DomainAnalysisResponse(
        data=data,
        message="Domain analysis completed.",
        success=True,
    )
