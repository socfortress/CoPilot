import requests

from app.auth.services.universal import get_scheduler_password


def scheduler_login():
    # Get the password
    password = get_scheduler_password()

    # Get an auth token
    token_response = requests.post(
        "http://localhost:5000/auth/token",
        headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "", "username": "scheduler", "password": password, "scope": ""},
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
