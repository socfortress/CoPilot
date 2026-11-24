"""E2E for migration c1328a0b1c2d (the cloud assessment tables, #1328). NOT collected by pytest:
it needs a live, disposable MySQL.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.4.13

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python tests/e2e/cloud_assessment_migration_e2e.py

Point it at a throwaway instance on 13306, never at the MySQL in .env: it migrates the
database down and up and writes rows.

What it proves, on real MySQL (8.4 without --restrict-fk-on-non-standard-key=OFF: the new keys
all point at unique keys):
- the whole chain upgrades to this revision, and the tables match the SQLModel models (Alembic's
  own comparison finds nothing to change);
- a customer's accounts, scans, check results and findings all go when the customer is deleted;
- an account name is unique per customer, a check once per scan;
- the widest values fit (a 1024-character resource id, a 512-character finding id, utf8mb4 text)
  and JSON round-trips;
- the downgrade drops the four tables and nothing else, and the upgrade runs again after it.
"""
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.db.universal_models  # noqa: E402,F401  (registers customers for the foreign key)
from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from app.cloud_assessment.models import cloud_assessment  # noqa: E402,F401
from app.db.db_session import SQLALCHEMY_DATABASE_URI  # noqa: E402

BEFORE = "38c2e85a670a"
REVISION = "c1328a0b1c2d"
TABLES = ("cloud_assessment_account", "cloud_assessment_scan", "cloud_assessment_check_result", "cloud_assessment_finding")
CUSTOMER = "E2E_1328"
OTHER = "E2E_1328_B"

URL = SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql")
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def alembic_cfg() -> Config:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = Config(os.path.join(here, "alembic", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", URL)
    cfg.set_main_option("script_location", os.path.join(here, "alembic"))
    return cfg


def q(conn, sql, **params):
    return conn.execute(text(sql), params)


def tables_present(conn) -> set:
    rows = q(
        conn,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name LIKE 'cloud_assessment_%'",
    )
    return {row[0] for row in rows}


def count(conn, table, customer) -> int:
    column = "customer_code"
    if table == "cloud_assessment_check_result":
        return q(
            conn,
            "SELECT COUNT(*) FROM cloud_assessment_check_result r JOIN cloud_assessment_scan s ON s.id = r.scan_id WHERE s.customer_code = :c",
            c=customer,
        ).scalar()
    return q(conn, f"SELECT COUNT(*) FROM {table} WHERE {column} = :c", c=customer).scalar()


def clean(conn):
    q(conn, "DELETE FROM customers WHERE customer_code IN (:a, :b)", a=CUSTOMER, b=OTHER)


def model_differences(conn) -> list:
    def ours(obj, name, type_, reflected, compare_to):
        table = name if type_ == "table" else getattr(getattr(obj, "table", None), "name", None)
        return table in TABLES

    context = MigrationContext.configure(conn, opts={"include_object": ours, "compare_type": True, "compare_server_default": True})
    return compare_metadata(context, SQLModel.metadata)


def add_account(conn, customer, name) -> int:
    q(
        conn,
        "INSERT INTO cloud_assessment_account (customer_code, name, provider, auth_method, config, secret_ciphertext, created_at, updated_at) "
        "VALUES (:c, :n, 'aws', 'role', :cfg, 'gAAAA-ciphertext', NOW(), NOW())",
        c=customer,
        n=name,
        cfg='{"role_arn": "arn:aws:iam::123456789012:role/ProwlerScan", "external_id": "copilot-x", "regions": ["eu-west-1"]}',
    )
    return q(conn, "SELECT LAST_INSERT_ID()").scalar()


def add_scan(conn, account_id, customer) -> int:
    q(
        conn,
        "INSERT INTO cloud_assessment_scan (account_id, customer_code, status, trigger_type, queued_at, fail_count, fail_critical, prowler_errors) "
        "VALUES (:a, :c, 'completed', 'schedule', NOW(), 3, 1, :errors)",
        a=account_id,
        c=customer,
        errors='["ClientError"]',
    )
    return q(conn, "SELECT LAST_INSERT_ID()").scalar()


def add_check(conn, scan_id, check_id):
    q(
        conn,
        "INSERT INTO cloud_assessment_check_result (scan_id, check_id, title, service, severity, compliance, fail_count) "
        "VALUES (:s, :k, 'Root account has MFA enabled', 'iam', 'critical', :comp, 1)",
        s=scan_id,
        k=check_id,
        comp='{"CIS-5.0": ["1.1"], "MITRE-ATTACK": ["T1552"]}',
    )


def add_finding(conn, scan_id, account_id, customer):
    q(
        conn,
        "INSERT INTO cloud_assessment_finding (scan_id, account_id, customer_code, finding_uid, finding_uid_hash, check_id, status, severity, "
        "status_extended, service, region, cloud_account_uid, cloud_account_name, resource_uid, resource_name, resource_type, resource_tags, "
        "first_seen_at) VALUES (:s, :a, :c, :uid, :h, 'iam_root_mfa_enabled', 'FAIL', 'high', :ext, 'iam', 'us-east-1', '123456789012', "
        "'production', :ruid, :rname, 'AwsIamUser', :tags, NOW())",
        s=scan_id,
        a=account_id,
        c=customer,
        uid="p" * 512,
        h="0" * 64,
        ext="MFA is not enabled for root account.",
        ruid="arn:aws:iam::123456789012:" + "r" * 998,
        rname="résumé-сервер-服务器\u202e",
        tags='["env:prod", "owner:team-a"]',
    )


def main() -> int:
    cfg = alembic_cfg()
    engine = create_engine(URL)

    print("== upgrade the whole chain")
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        clean(conn)
        check("the four tables exist", tables_present(conn) == set(TABLES), sorted(tables_present(conn)))
        differences = model_differences(conn)
        check("the tables match the models", differences == [], repr(differences)[:400])
        rules = dict(
            q(
                conn,
                "SELECT CONCAT(table_name, '.', referenced_table_name), delete_rule FROM information_schema.referential_constraints "
                "WHERE constraint_schema = DATABASE() AND table_name LIKE 'cloud_assessment_%'",
            ).fetchall(),
        )
        check(
            "every key cascades",
            rules
            == {
                "cloud_assessment_account.customers": "CASCADE",
                "cloud_assessment_scan.cloud_assessment_account": "CASCADE",
                "cloud_assessment_check_result.cloud_assessment_scan": "CASCADE",
                "cloud_assessment_finding.cloud_assessment_scan": "CASCADE",
            },
            rules,
        )

    print("== rows, limits and cascades")
    with engine.begin() as conn:
        q(conn, "INSERT INTO customers (customer_code, customer_name, created_at) VALUES (:c, 'E2E 1328', NOW())", c=CUSTOMER)
        q(conn, "INSERT INTO customers (customer_code, customer_name, created_at) VALUES (:c, 'E2E 1328 B', NOW())", c=OTHER)
        account = add_account(conn, CUSTOMER, "Production")
        other_account = add_account(conn, OTHER, "Production")  # the same name for another customer is fine
        scan = add_scan(conn, account, CUSTOMER)
        other_scan = add_scan(conn, other_account, OTHER)
        add_check(conn, scan, "iam_root_mfa_enabled")
        add_check(conn, other_scan, "iam_root_mfa_enabled")
        add_finding(conn, scan, account, CUSTOMER)
        add_finding(conn, other_scan, other_account, OTHER)
        stored = q(
            conn,
            "SELECT CHAR_LENGTH(resource_uid), CHAR_LENGTH(finding_uid), resource_name, JSON_EXTRACT(resource_tags, '$[1]') "
            "FROM cloud_assessment_finding WHERE customer_code = :c",
            c=CUSTOMER,
        ).one()
        check("the widest values and utf8mb4 text fit", stored[:3] == (1024, 512, "résumé-сервер-服务器\u202e"), stored)
        check("JSON round-trips", stored[3] == '"owner:team-a"', stored[3])
        defaults = q(
            conn,
            "SELECT enabled, schedule, muted, is_new, pass_count FROM cloud_assessment_account a JOIN cloud_assessment_scan s ON s.account_id = a.id JOIN cloud_assessment_finding f ON f.scan_id = s.id WHERE a.id = :a",
            a=account,
        ).one()
        check("defaults apply", tuple(defaults) == (1, "off", 0, 0, 0), defaults)

    for statement, name in (
        (lambda conn: add_account(conn, CUSTOMER, "Production"), "an account name is unique per customer"),
        (lambda conn: add_check(conn, scan, "iam_root_mfa_enabled"), "a check is stored once per scan"),
    ):
        try:
            with engine.begin() as conn:
                statement(conn)
            check(name, False, "the duplicate was accepted")
        except IntegrityError:
            check(name, True)

    with engine.begin() as conn:
        q(conn, "DELETE FROM customers WHERE customer_code = :c", c=CUSTOMER)
        left = {table: count(conn, table, CUSTOMER) for table in TABLES}
        check("deleting a customer deletes its accounts, scans, checks and findings", set(left.values()) == {0}, left)
        kept = {table: count(conn, table, OTHER) for table in TABLES}
        check("and nothing of another customer's", set(kept.values()) == {1}, kept)

    print("== downgrade and upgrade again")
    command.downgrade(cfg, BEFORE)
    with engine.begin() as conn:
        check("the downgrade drops the four tables", tables_present(conn) == set(), sorted(tables_present(conn)))
        customers_left = q(conn, "SELECT COUNT(*) FROM customers WHERE customer_code = :c", c=OTHER).scalar()
        check("and leaves the customers table alone", customers_left == 1, customers_left)
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        check("the upgrade runs again", tables_present(conn) == set(TABLES))
        check("still matching the models", model_differences(conn) == [])
        version = q(conn, "SELECT version_num FROM alembic_version").scalar()
        check("at the new head", version == REVISION, version)
        clean(conn)
    engine.dispose()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
