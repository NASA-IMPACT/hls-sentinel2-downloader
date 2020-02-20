#!/bin/bash

apt update -y
apt install -y docker docker.io awscli

aws configure set region us-east-1
`aws ecr get-login --no-include-email`
docker pull ${DOCKER_IMAGE}

mkfs -t ext4 /dev/nvme0n1
mkdir -p /mnt/files
mount /dev/nvme0n1 /mnt/files/



echo 'export COPERNICUS_USERNAME=${COPERNICUS_USERNAME}' >> /home/ubuntu/.bash_profile
echo 'export COPERNICUS_PASSWORD=${COPERNICUS_PASSWORD}' >> /home/ubuntu/.bash_profile
echo 'export UPLOAD_BUCKET=${UPLOAD_BUCKET}' >> /home/ubuntu/.bash_profile
echo 'export DOCKER_IMAGE=${DOCKER_IMAGE}' >> /home/ubuntu/.bash_profile
echo 'export DB_URL=${DB_URL}' >> /home/ubuntu/.bash_profile

echo "alias sudo='sudo '" >> /home/ubuntu/.bash_profile
echo "alias run_docker='docker run -p 6800:6800 -e DB_URL=${DB_URL} -e COPERNICUS_USERNAME=${COPERNICUS_USERNAME} -e COPERNICUS_PASSWORD=${COPERNICUS_PASSWORD} -e UPLOAD_BUCKET=${UPLOAD_BUCKET} -e DOWNLOADS_PATH=/mnt/files -v /mnt/files:/mnt/files ${DOCKER_IMAGE}'" >> /home/ubuntu/.bash_profile
