#!/bin/bash
# Script to run GDP task on AWS Fargate

echo "[*] Starting GDP Fargate Task..."

aws ecs run-task \
  --cluster gdp-cluster \
  --task-definition last-10-years-gdp-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-05af49114c7393c39],securityGroups=[sg-0b8eaca97d7cfe13b],assignPublicIp=ENABLED}" \
  --region eu-west-1

echo "[+] Task started! Check CloudWatch logs:"
echo "    Log Group: /ecs/last-10-years-gdp"
echo "    Region: eu-west-1"
