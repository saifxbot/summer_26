import json
import os

import boto3
from botocore.exceptions import ClientError


SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INFRA_DIR = os.path.join(PROJECT_ROOT, 'infra')

TABLE_DEF_PATH = os.path.join(INFRA_DIR, 'dynamodb-state-table.json')
TASK_ROLE_POLICY_PATH = os.path.join(INFRA_DIR, 'task-role-policy.json')
TRUST_POLICY_PATH = os.path.join(INFRA_DIR, 'trust-policy.json')

REGION = os.environ.get('AWS_REGION', 'eu-west-1')

TABLE_NAME = 'summer-26-pipeline-state'
TASK_ROLE_NAME = 'ecsTaskRole'
TASK_ROLE_POLICY_NAME = 'summer-26-pipeline-task-policy'


def provision_table():
    """
    Create the pipeline state table in DynamoDB if it does not exist.

    Purpose:
        Reads infra/dynamodb-state-table.json so the table schema lives in
        the repo. Idempotent: skips creation when the table already exists.
    """
    with open(TABLE_DEF_PATH, encoding='utf-8') as handle:
        table_def = json.load(handle)

    dynamodb = boto3.client('dynamodb', region_name=REGION)

    try:
        dynamodb.describe_table(TableName=TABLE_NAME)
        print(f"[!] Table {TABLE_NAME} already exists, skipping creation...")
        return
    except ClientError as error:
        if error.response['Error']['Code'] != 'ResourceNotFoundException':
            raise

    print(f"[*] Creating DynamoDB table {TABLE_NAME}...")

    dynamodb.create_table(
        TableName=table_def['TableName'],
        AttributeDefinitions=table_def['AttributeDefinitions'],
        KeySchema=table_def['KeySchema'],
        BillingMode=table_def['BillingMode'],
    )

    dynamodb.get_waiter('table_exists').wait(TableName=TABLE_NAME)

    print(f"[+] Table {TABLE_NAME} created successfully!")


def ensure_task_role_policy():
    """
    Ensure ecsTaskRole exists and carries the pipeline inline policy.

    Purpose:
        The ECS tasks run under the ecsTaskRole, which needs s3:GetObject
        (S3 merge) and DynamoDB access on the state table. Creates the role
        from infra/trust-policy.json when missing, then applies the policy
        from infra/task-role-policy.json (put-role-policy is idempotent).
    """
    iam = boto3.client('iam', region_name=REGION)

    try:
        iam.get_role(RoleName=TASK_ROLE_NAME)
        print(f"[!] Role {TASK_ROLE_NAME} already exists, skipping creation...")
    except ClientError as error:
        if error.response['Error']['Code'] != 'NoSuchEntity':
            raise

        with open(TRUST_POLICY_PATH, encoding='utf-8') as handle:
            trust_policy = json.load(handle)

        print(f"[*] Creating IAM role {TASK_ROLE_NAME}...")

        iam.create_role(
            RoleName=TASK_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )

        print(f"[+] Role {TASK_ROLE_NAME} created successfully!")

    with open(TASK_ROLE_POLICY_PATH, encoding='utf-8') as handle:
        role_policy = json.load(handle)

    print(f"[*] Applying inline policy {TASK_ROLE_POLICY_NAME} to {TASK_ROLE_NAME}...")

    iam.put_role_policy(
        RoleName=TASK_ROLE_NAME,
        PolicyName=TASK_ROLE_POLICY_NAME,
        PolicyDocument=json.dumps(role_policy),
    )

    print(f"[+] Policy {TASK_ROLE_POLICY_NAME} applied successfully!")


def main():
    print(f"[*] Provisioning DynamoDB for summer-26 pipeline (region {REGION})...")

    provision_table()
    ensure_task_role_policy()

    print("[+] DynamoDB provisioning complete!")


if __name__ == "__main__":
    main()
