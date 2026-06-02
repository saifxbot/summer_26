# Check Fargate task status and logs

Write-Host "[*] Checking GDP Fargate Task Status..." -ForegroundColor Cyan
Write-Host ""

# Get all tasks (running or stopped)
$tasks = aws ecs list-tasks --cluster gdp-cluster --region eu-north-1 --query 'taskArns[0]' --output text

if ($tasks -and $tasks -ne "None" -and $tasks -ne "") {
    Write-Host "[+] Found Task: $tasks" -ForegroundColor Green
    Write-Host ""
    
    # Extract task ID (last part of ARN)
    $taskId = $tasks -split '/' | Select-Object -Last 1
    Write-Host "[*] Task ID: $taskId" -ForegroundColor Yellow
    Write-Host ""
    
    # Get task details
    Write-Host "[*] Task Details:" -ForegroundColor Cyan
    $details = aws ecs describe-tasks --cluster gdp-cluster --tasks $taskId --region eu-north-1 --output json | ConvertFrom-Json
    $task = $details.tasks[0]
    
    Write-Host "    Status: $($task.lastStatus)" -ForegroundColor Yellow
    Write-Host "    Desired: $($task.desiredStatus)" -ForegroundColor Yellow
    Write-Host "    Created: $($task.createdAt)" -ForegroundColor Yellow
    Write-Host "    Container Status: $($task.containers[0].lastStatus)" -ForegroundColor Yellow
    Write-Host ""
    
    # Get logs
    Write-Host "[*] Getting Logs..." -ForegroundColor Cyan
    
    # List available log streams
    $streams = aws logs describe-log-streams --log-group-name "/ecs/last-10-years-gdp" --region eu-north-1 --query 'logStreams[*].logStreamName' --output text
    
    if ($streams -and $streams -ne "") {
        Write-Host "[+] Found log stream: $streams" -ForegroundColor Green
        Write-Host ""
        Write-Host "[*] Log Output:" -ForegroundColor Yellow
        aws logs get-log-events --log-group-name "/ecs/last-10-years-gdp" --log-stream-name $streams --region eu-north-1 --query 'events[*].[message]' --output text
    } else {
        Write-Host "[!] No logs yet - task is still provisioning..." -ForegroundColor Yellow
        Write-Host "[*] Wait 10-15 seconds and try again." -ForegroundColor Cyan
    }
} else {
    Write-Host "[!] No tasks found" -ForegroundColor Red
    Write-Host "[*] Run: .\run-fargate-task.ps1" -ForegroundColor Yellow
}
