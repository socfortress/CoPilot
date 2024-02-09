from datetime import datetime

from loguru import logger


def parse_date(date_string: str) -> datetime:
    """
    Parses a date string into a datetime object.

    Args:
        date_string (str): The date string to parse.

    Returns:
        datetime: The parsed datetime object.
    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S+00:00")
    except ValueError:
        logger.info(
            f"Invalid format for date: {date_string}. Using the epoch time as default.",
        )
        return datetime.strptime("1970-01-01T00:00:00+00:00", "%Y-%m-%dT%H:%M:%S+00:00")
