from typing import Any
from typing import Optional

import dnstwist
from loguru import logger


class DNSTwistService:
    """
    Service for handling operations related to dnstwist.

    Attributes:
        domain (Optional[str]): Domain to be analyzed by dnstwist.
    """

    def __init__(self, domain: Optional[str] = None):
        """
        Initialize a DNSTwistService instance.

        Args:
            domain (Optional[str]): Domain to be analyzed by dnstwist.
        """
        self.domain = domain

    def set_domain(self, domain: str) -> None:
        """
        Set the domain to be analyzed by dnstwist.

        Args:
            domain (str): Domain to be analyzed.
        """
        self.domain = domain

    def analyze_domain_registered(self) -> Any:
        """
        Analyze the domain using dnstwist and return the results for registered domains.

        Returns:
            Any: Results of the dnstwist analysis.
        """
        if self.domain is None:
            raise ValueError("Domain must be set before analysis.")

        logger.info("Analyzing domain for registered domains.")
        data = dnstwist.run(domain=self.domain, registered=True, format="json")
        logger.debug(f"Data: {data}")
        return {"message": "Successfully analyzed domain.", "success": True, "data": data}

    def analyze_domain_phishing(self) -> Any:
        """
        Analyze the domain using dnstwist and the lsh ssdeep which extracts the html from the domain's root site
         and compares that to similar domains to detect cloned websites.

        Returns:
            Any: Results of the dnstwist analysis.
        """
        if self.domain is None:
            raise ValueError("Domain must be set before analysis.")

        logger.info("Analyzing domain for potential phishing.")
        data = dnstwist.run(
            domain=self.domain,
            registered=True,
            format="json",
            lsh=True,
        )
        logger.debug(f"Data: {data}")
        return {"message": "Successfully analyzed domain.", "success": True, "data": data}
