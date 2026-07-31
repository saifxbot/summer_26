# Last 10 Years GDP Container

This container runs the existing `last_10_years_gdp.py` script, which calls the Alpha Vantage `REAL_GDP` endpoint and prints the latest GDP values.

## Project Layout

- `src/` contains the Python application code.
- `scripts/` contains AWS and Fargate helper scripts.
- `infra/` contains ECS task and IAM policy files.
- `tests/` contains the lightweight test/scratch scripts.

## Build

powershell
docker build -t last-10-years-gdp .


## Run

powershell
docker run --rm last-10-years-gdp


## AWS ECR

powershell
aws ecr create-repository --repository-name last-10-years-gdp
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker tag last-10-years-gdp:latest <account-id>.dkr.ecr.<region>.amazonaws.com/last-10-years-gdp:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/last-10-years-gdp:latest

## AWS ECS Fargate

1. Create an ECS cluster using the Fargate launch type.
2. Use `infra/task-definition.json` as the task definition template with the pushed ECR image.
3. Set CPU and memory values appropriate for a small Python job.
4. Run the task manually with `scripts/run-fargate-task.ps1` or `scripts/run-fargate-task.sh`, or create a Fargate service if you want it always on.
5. Ensure the task execution role can pull from ECR and write logs to CloudWatch.
6. For production, pass the Alpha Vantage API key as an ECS secret or environment variable instead of hardcoding it in the image.

## CloudWatch Logs

In the ECS task definition, configure the `awslogs` log driver with a log group, region, and stream prefix. Then open CloudWatch Logs and view the log stream created for the task.