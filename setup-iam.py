import json
import subprocess
import sys

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

# Write to file
with open('trust-policy.json', 'w') as f:
    json.dump(trust_policy, f)

print("[*] Creating IAM role for ECS...")

# Create role
result = subprocess.run([
    'aws', 'iam', 'create-role',
    '--role-name', 'ecsTaskExecutionRole',
    '--assume-role-policy-document', 'file://trust-policy.json',
    '--region', 'eu-north-1'
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
    '--region', 'eu-north-1'
], capture_output=True, text=True)

if result.returncode == 0:
    print("[+] Policy attached successfully!")
else:
    print("[!] Error:", result.stderr)

print("[*] IAM setup complete!")
