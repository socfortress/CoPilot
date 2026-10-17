"""One password policy for the API and both frontends (#1265).

A Customer Portal user could not change their password to one that met every rule the
error message listed: the reset schema allowed only letters, digits and @$!%*?&#, so a
single '-' or '_' failed it. The create schema, the reset schemas, the analyst
frontend and the portal each had their own rule. Now every password a user chooses
goes through ``app/auth/schema/password_policy.py``, and each frontend's
``src/utils/password-policy.ts`` is checked against the same cases.

Run with: cd backend && python -m pytest tests/test_password_policy.py
"""

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from pydantic import ValidationError  # noqa: E402

from app.auth.models.users import Password  # noqa: E402
from app.auth.models.users import PasswordReset  # noqa: E402
from app.auth.models.users import PasswordResetToken  # noqa: E402
from app.auth.models.users import UserInput  # noqa: E402
from app.auth.schema.password_policy import PASSWORD_PROBLEMS  # noqa: E402
from app.auth.schema.password_policy import PASSWORD_REQUIREMENTS  # noqa: E402
from app.auth.schema.password_policy import password_problem_code  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
CASES_PATH = BACKEND / "tests" / "fixtures" / "password_policy_cases.json"
FRONTEND_COPIES = [
    REPO / "frontend" / "src" / "utils" / "__tests__" / "fixtures" / "password-policy-cases.json",
    REPO / "customer-portal" / "src" / "utils" / "__tests__" / "fixtures" / "password-policy-cases.json",
]
TS_POLICIES = [
    REPO / "frontend" / "src" / "utils" / "password-policy.ts",
    REPO / "customer-portal" / "src" / "utils" / "password-policy.ts",
]

FIXTURE = json.loads(CASES_PATH.read_text())
CASES = FIXTURE["cases"]
ACCEPTED = [case["password"] for case in CASES if case["problem"] is None]
REFUSED = [case for case in CASES if case["problem"] is not None]


def _id(case):
    return f"{case['problem'] or 'ok'}: {case['note'] or repr(case['password'])[:24]}"


@pytest.mark.parametrize("case", CASES, ids=[_id(case) for case in CASES])
def test_policy_matches_the_shared_cases(case):
    assert password_problem_code(case["password"]) == case["problem"]


def test_a_lone_surrogate_is_refused():
    # Not in the shared cases: Vite's JSON parser refuses a lone surrogate escape.
    assert password_problem_code("Aa1!aaaa\ud800") == "control_character"


def test_messages_and_requirements_match_the_shared_cases():
    assert PASSWORD_PROBLEMS == FIXTURE["messages"]
    assert PASSWORD_REQUIREMENTS == FIXTURE["requirements"]


def _schemas(password):
    """Every schema that takes a password a user chooses."""
    return [
        lambda: UserInput(username="new", password=password, email="new@example.com"),
        lambda: PasswordReset(username="customer", new_password=password),
        lambda: PasswordReset(username="customer", current_password="Old-Passw0rd", new_password=password),
        lambda: PasswordResetToken(username="customer", reset_token="token", new_password=password),
    ]


@pytest.mark.parametrize("password", ACCEPTED)
def test_every_schema_accepts_a_compliant_password(password):
    for build in _schemas(password):
        build()


@pytest.mark.parametrize("case", REFUSED, ids=[_id(case) for case in REFUSED])
def test_every_schema_refuses_with_the_rule_it_breaks(case):
    for build in _schemas(case["password"]):
        with pytest.raises(ValidationError) as raised:
            build()
        assert PASSWORD_PROBLEMS[case["problem"]] in str(raised.value)


def test_the_issue_password_is_accepted_by_the_reset_schema():
    # #1265: compliant, but '-' was outside the old allow-list.
    assert PasswordReset(username="customer", new_password="Password1!-x").new_password == "Password1!-x"


@pytest.mark.parametrize("length", [8, 12, 24, 72])
def test_generated_passwords_meet_the_policy(length):
    # Temporary passwords and the seeded system users come from Password.generate.
    for _ in range(50):
        assert password_problem_code(Password.generate(length).plain) is None


@pytest.mark.parametrize("copy", FRONTEND_COPIES, ids=lambda path: path.parts[-6])
def test_frontend_cases_are_the_same_cases(copy):
    if not copy.exists():
        pytest.skip(f"{copy} not in this checkout")
    assert json.loads(copy.read_text()) == FIXTURE


def test_both_frontends_carry_the_same_policy_module():
    if not all(path.exists() for path in TS_POLICIES):
        pytest.skip("frontend sources not in this checkout")
    assert TS_POLICIES[0].read_text() == TS_POLICIES[1].read_text()
