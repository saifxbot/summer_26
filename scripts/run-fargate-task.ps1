# Script to run GDP task on AWS Fargate
# Usage: .\run-fargate-task.ps1

Write-Host "[*] Starting GDP Fargate Task on AWS..." -ForegroundColor Cyan

$clusterName = "gdp-cluster"
$taskDefinition = "last-10-years-gdp-task"
$subnet = "subnet-05af49114c7393c39"
$securityGroup = "sg-0b8eaca97d7cfe13b"
$region = "eu-west-1"

aws ecs run-task `
  --cluster $clusterName `
  --task-definition $taskDefinition `
  --launch-type FARGATE `
  --network-configuration "awsvpcConfiguration={subnets=[$subnet],securityGroups=[$securityGroup],assignPublicIp=ENABLED}" `
  --region $region

if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Failed to start task. Check the AWS error above." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[+] Task Started Successfully!" -ForegroundColor Green
Write-Host "    Cluster: $clusterName" -ForegroundColor Yellow
Write-Host "    Task Definition: $taskDefinition" -ForegroundColor Yellow
Write-Host ""
Write-Host "[*] View Logs:" -ForegroundColor Cyan
Write-Host "    Log Group: /ecs/last-10-years-gdp" -ForegroundColor Yellow
Write-Host "    Region: $region" -ForegroundColor Yellow
Write-Host ""
Write-Host "[*] Check task status:" -ForegroundColor Cyan
Write-Host "    aws ecs list-tasks --cluster $clusterName --region $region" -ForegroundColor Gray
