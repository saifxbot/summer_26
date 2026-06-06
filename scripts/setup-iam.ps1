# PowerShell script to create IAM execution role for ECS
# This script creates the role and attaches the necessary policies

Write-Host "[*] Creating IAM role for ECS Fargate..." -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$infraDir = Join-Path $projectRoot "infra"
$trustPolicyPath = Join-Path $infraDir "trust-policy.json"

# Create trust policy JSON file
$trustPolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = @{
                Service = "ecs-tasks.amazonaws.com"
            }
            Action = "sts:AssumeRole"
        }
    )
}

New-Item -ItemType Directory -Force -Path $infraDir | Out-Null
$trustPolicy | ConvertTo-Json | Out-File -FilePath $trustPolicyPath -Encoding UTF8

# Create the role
Write-Host "[*] Creating ecsTaskExecutionRole..." -ForegroundColor Yellow
$output = aws iam create-role --role-name ecsTaskExecutionRole `
  --assume-role-policy-document file://$trustPolicyPath `
    --region eu-west-1 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "[+] Role created successfully!" -ForegroundColor Green
} elseif ($output -match "EntityAlreadyExists") {
    Write-Host "[!] Role already exists - skipping creation" -ForegroundColor Yellow
} else {
    Write-Host "[!] Error creating role: $output" -ForegroundColor Red
}

# Attach the managed policy
Write-Host "[*] Attaching AmazonECSTaskExecutionRolePolicy..." -ForegroundColor Yellow
$output = aws iam attach-role-policy `
  --role-name ecsTaskExecutionRole `
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy `
    --region eu-west-1 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "[+] Policy attached successfully!" -ForegroundColor Green
} else {
    Write-Host "[!] Error attaching policy: $output" -ForegroundColor Red
}

Write-Host "[+] IAM role setup complete!" -ForegroundColor Green
