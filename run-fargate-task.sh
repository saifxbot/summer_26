#!/bin/bash
# Script to run GDP task on AWS Fargate

echo "[*] Starting GDP Fargate Task..."

aws ecs run-task \
  --cluster gdp-cluster \
  --task-definition last-10-years-gdp-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-06689d8919ecd8b3f],securityGroups=[sg-06b5531549418375d],assignPublicIp=ENABLED}" \
  --region eu-north-1

echo "[+] Task started! Check CloudWatch logs:"
echo "    Log Group: /ecs/last-10-years-gdp"
echo "    Region: eu-north-1"
