import os

import requests
from app.auth.services.universal import get_scheduler_password
from dotenv import load_dotenv

load_dotenv()


def scheduler_login():
    """
    Retrieves an authentication token for the scheduler user.

    Returns:
        dict: The headers containing the authentication token.
              Returns None if the token retrieval fails.
    """
    # Get the password
    password = get_scheduler_password()

    # Get an auth token
    token_response = requests.post(
        f"http://{os.getenv('SERVER_IP')}:5000/auth/token",
        headers={
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "",
            "username": "scheduler",
            "password": password,
            "scope": "",
        },
    )

    # Check if the token was successfully retrieved
    if token_response.status_code == 200:
        token = token_response.json().get("access_token")
        # Use the token in the header of your subsequent requests
        headers = {"Authorization": f"Bearer {token}"}
        return headers
    else:
        print("Failed to retrieve token")
        return None
