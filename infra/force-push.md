## Export AWS credentials

```bash
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
```

## Build and push Docker image

**Run these from the repository root** (the folder that contains `infra/` and the `Dockerfile`), not from `infra/`. Use `--platform linux/amd64` so ECS Fargate can pull the image (required on Apple Silicon).

From repo root:

```bash
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 296410404869.dkr.ecr.us-west-2.amazonaws.com
docker build --platform linux/amd64 -t 296410404869.dkr.ecr.us-west-2.amazonaws.com/hack-europe:latest .
docker push 296410404869.dkr.ecr.us-west-2.amazonaws.com/hack-europe:latest
aws ecs update-service --cluster hack-europe-cluster --service hack-europe-service --force-new-deployment --region us-west-2
```

Or from repo root: `npm run deploy:ecr` (builds with correct platform), then run the `docker push` and `aws ecs update-service` lines above.
