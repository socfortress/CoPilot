import regex
from loguru import logger


class UniversalService:
    """
    Service for handling universal checks regardless of alert type.

    Attributes:
        _config_manager (Optional[ConfigManager]): ConfigManager object for accessing the config file.
        _excluded_rule_ids (Optional[set[str]]): Set of rule ids that are excluded.
        _valid_customer_codes (Optional[Dict[str, Tuple[int, str, str]]]):
            Dictionary mapping customer codes to their corresponding data.
    """

    def __init__(self):
        """
        Initialize a UniversalService instance.
        """

    @staticmethod
    def is_domain(domain: str) -> bool:
        """
        Check if the provided domain is valid.

        Args:
            domain (str): The domain to check.

        Returns:
            bool: True if the domain is valid, False otherwise.
        """
        logger.info(f"Checking if domain {domain} is valid.")
        pattern = regex.compile(
            r"^(?:[a-zA-Z0-9]+([-._]?[a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,}$",
        )
        return bool(pattern.match(domain))
