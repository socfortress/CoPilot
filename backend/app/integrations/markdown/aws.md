Collect AWS **CloudTrail** and **GuardDuty** logs from a customer's S3 bucket with the Wazuh `aws-s3` module, and route them into the customer's own Graylog streams and Grafana datasources.

# How it works

The Wazuh **master** reads the logs. It is the manager CoPilot's _Wazuh Manager_ connector points at. One `<wodle name="aws-s3">` block in its `ossec.conf` holds every customer's `<bucket>` entries.

Deploying an AWS integration in CoPilot:

1. **Checks the credentials against AWS first.** It confirms the key belongs to `AWS_ACCOUNT_ID`, that the bucket is readable, and that each service has logs. It also reads one byte of a recent log, which proves `s3:GetObject` and, for GuardDuty, `kms:Decrypt`. If a check fails, **nothing is changed**.
    - If CoPilot cannot reach AWS at all (no route out), the checks are skipped with a warning. The Wazuh master reports problems in its own `ossec.log`.
2. **Adds this account's `<bucket>` entries to the aws-s3 wodle**, then restarts the manager. It creates the wodle if it is missing.
    - Other customers' buckets and the wodle's own settings are never touched.
    - CoPilot refuses to write a file that differs from the manager's in anything else.
    - CoPilot re-reads the file just before writing.
    - CoPilot asks the manager to validate the new file before restarting. If validation fails, it restores the original.
3. **Creates, per service, a Graylog index set** (`<service>-<customer_code>`, daily rotation, 30 indices, no replicas) **and a stream.**
    - The stream matches the bucket, the service and the account.
    - Events come from the master (agent `000`) with no customer label, so routing is by AWS account.
    - The `AWS PROCESSING PIPELINE` sets `syslog_type: aws`, `timestamp_utc`, `syslog_level` and `aws_account_id`.
4. **Creates an "AWS" Grafana folder and one datasource per service.** No AWS dashboards are provisioned yet.

If any step fails, everything the deployment created is rolled back.

# Customer-side setup

The customer creates a read-only IAM user and sends the access key. The full guide is in SOCFortress KB articles **AR-1138** and **AR-1139**. The user needs:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
            "Resource": "arn:aws:s3:::<bucket-name>"
        },
        {
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::<bucket-name>/*"
        },
        {
            "Effect": "Allow",
            "Action": "kms:Decrypt",
            "Resource": "arn:aws:kms:<region>:<account-id>:key/<guardduty-export-key-id>"
        }
    ]
}
```

GuardDuty exports are always KMS-encrypted. The export key's **key policy** must also allow the IAM user to decrypt.

# Auth keys

| Key                   | Required | Example                          | Notes                                                                              |
| --------------------- | -------- | -------------------------------- | ---------------------------------------------------------------------------------- |
| `ACCESS_KEY_ID`       | yes      | `AKIA…`                          | Access key of the read-only IAM user                                               |
| `SECRET_ACCESS_KEY`   | yes      | —                                | Write-only: CoPilot never shows it again. Leave it blank when editing to keep it.  |
| `AWS_ACCOUNT_ID`      | yes      | `123456789012`                   | 12 digits. Alerts are routed to the customer by this account.                      |
| `AWS_ACCOUNT_ALIAS`   | no       | `production`                     | Label only                                                                         |
| `AWS_ORGANIZATION_ID` | no       | `o-a1b2c3d4e5`                   | CloudTrail **organization trails** only                                            |
| `BUCKET_NAME`         | yes      | `example-cloudtrail-logs`        |                                                                                    |
| `SERVICES`            | yes      | `cloudtrail,guardduty:guardduty` | `service` or `service:s3-prefix`, comma-separated                                  |
| `ONLY_LOGS_AFTER`     | no       | `2026-OCT-08`                    | `YYYY-MMM-DD`. Defaults to the day of the first deployment.                        |

`SERVICES` names each service and, after a colon, the S3 prefix it exports under. It is the part before `AWSLogs/` in the bucket. For example, GuardDuty exporting to `s3://bucket/guardduty/AWSLogs/<account>/GuardDuty/` is `guardduty:guardduty`. CloudTrail with no trail prefix is just `cloudtrail`.

Supported services: **cloudtrail**, **guardduty**. Others (VPC flow logs, load balancers, server access logs, …) are refused until they have been verified against real events.

# Several AWS accounts per customer

A customer can have one AWS integration **instance per account and bucket**. Give every instance after the first a name.

- The index sets, Grafana datasources and folder are **shared** by the customer's accounts. Each event still names its account.
- Each instance gets its **own streams**.
- An AWS account can belong to one customer only.

# Re-sync, key rotation and removal

- **Sync** (on a deployed instance) applies the current auth keys:
    - a rotated key updates the `<access_key>`/`<secret_key>` of this instance's buckets;
    - a service added to `SERVICES` is deployed;
    - a service removed from it is torn down, unless another account of the customer still collects that service, in which case its index set and datasource are kept.
- `AWS_ACCOUNT_ID` and `BUCKET_NAME` **cannot be changed** on a deployed instance: they identify its buckets and streams. To change them, delete the instance and add it again.
- **Deleting** an instance removes:
    - its buckets from the manager (and the wodle when it is the last), then restarts the manager;
    - its streams;
    - the shared index set, datasource and folder once no other account of the customer needs them.

# Action required on the Wazuh master: `/root/.aws/config`

The Wazuh API can only edit `ossec.conf`, so **CoPilot cannot read or write `/root/.aws/config`**.

If that file exists on the master, it **must contain a `[default]` section**. Otherwise the aws-s3 module stops with **exit code 23** for every bucket that has no `aws_profile`, which is every bucket CoPilot provisions. The manager then logs `wazuh-modulesd:aws-s3: WARNING: … No profile named: 'default' was found in the user config file`.

After every deployment CoPilot shows these steps. It also watches the manager's log for the error and says so if it sees it.

1. On the Wazuh master, check whether the file exists: `sudo ls -l /root/.aws/config`.
2. If it exists and has no `[default]` section, add one. Keep any existing `[profile …]` sections:
    ```ini
    [default]
    region = <bucket region, e.g. eu-west-1>
    ```
3. Restart the manager: `sudo systemctl restart wazuh-manager`.
4. Confirm that `/var/ossec/logs/ossec.log` no longer reports `No profile named`.

If the file does not exist, nothing needs doing.

# Known trade-off: inline credentials

The access key is written into `ossec.conf` as `<access_key>` / `<secret_key>`. Wazuh documents these as deprecated since 4.4. Wazuh 4.14 still honours them, and only prints a deprecation notice.

They are the only option CoPilot can manage end to end. The alternative, `aws_profile`, needs `/root/.aws/credentials`, which the Wazuh API cannot write.

Office365 stores its `client_secret` in `ossec.conf` the same way. Anyone who can read `ossec.conf` through the Wazuh API can read these keys, so keep the IAM user read-only.
