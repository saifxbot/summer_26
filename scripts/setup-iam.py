import json
import os
import subprocess


SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INFRA_DIR = os.path.join(PROJECT_ROOT, 'infra')
TRUST_POLICY_PATH = os.path.join(INFRA_DIR, 'trust-policy.json')

# Create trust relationship policy
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

os.makedirs(INFRA_DIR, exist_ok=True)

# Write to file
with open(TRUST_POLICY_PATH, 'w', encoding='utf-8') as f:
    json.dump(trust_policy, f)

print("[*] Creating IAM role for ECS...")

# Create role
result = subprocess.run([
    'aws', 'iam', 'create-role',
    '--role-name', 'ecsTaskExecutionRole',
    '--assume-role-policy-document', f'file://{TRUST_POLICY_PATH}',
    '--region', 'eu-west-1'
], capture_output=True, text=True)

if "EntityAlreadyExists" in result.stderr or "already exists" in result.stderr:
    print("[!] Role already exists, skipping creation...")
else:
    if result.returncode == 0:
        print("[+] Role created successfully!")
        print(result.stdout)
    else:
        print("[!] Error:", result.stderr)

# Attach managed policy
print("[*] Attaching execution policy...")
result = subprocess.run([
    'aws', 'iam', 'attach-role-policy',
    '--role-name', 'ecsTaskExecutionRole',
    '--policy-arn', 'arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy',
    '--region', 'eu-west-1'
], capture_output=True, text=True)

if result.returncode == 0:
    print("[+] Policy attached successfully!")
else:
    print("[!] Error:", result.stderr)

print("[*] IAM setup complete!")
