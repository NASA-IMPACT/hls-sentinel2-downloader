#!/bin/sh
set -e

echo "Creating docker image"
DOCKER_NAME="hls-sentinel2-downloader"
DOCKER_TAG="$DOCKER_NAME:latest"
docker build . -t $DOCKER_NAME
echo "Docker image created"

echo "Creating ECR repository"
cd terraform
terraform apply -auto-approve --target=aws_ecr_repository.downloader
ECR_URL="$(terraform output | grep 'ecr_repository_url' | cut -f3- -d' '):latest"
echo "ECR repository created"

echo "Pushing the docker image"
docker tag $DOCKER_TAG $ECR_URL
`aws ecr get-login --no-include-email`
docker push $ECR_URL
echo "Docker image pushed"

echo "Deploying rest of the stack"
terraform apply -auto-approve
echo "Stack fully deployed"
echo "SUCCESS!"

cd ..
