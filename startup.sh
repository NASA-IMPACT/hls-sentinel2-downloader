#!/bin/bash

apt update -y
apt install -y docker docker.io awscli

aws configure set region us-west-2
`aws ecr get-login --no-include-email`
docker pull ${DOCKER_IMAGE}

mkfs -t ext4 /dev/nvme0n1
mkdir -p /mnt/files
mount /dev/nvme0n1 /mnt/files/



DOCKER_CMD="sudo docker run -d -e DB_URL=${DB_URL} -e COPERNICUS_USERNAME=${COPERNICUS_USERNAME} -e COPERNICUS_PASSWORD=${COPERNICUS_PASSWORD} -e UPLOAD_BUCKET=${UPLOAD_BUCKET} -e DOWNLOADS_PATH=/mnt/files -v /mnt/files:/mnt/files ${DOCKER_IMAGE}"
echo $DOCKER_CMD >> /home/ubuntu/run_docker.sh

DOCKER_CMD_TEST="sudo docker run -d \$@ -e MAX_DOWNLOADS=100 -e DAYS_GAP=10 -e JUST_MAIN=TRUE -e DB_URL=${DB_URL} -e COPERNICUS_USERNAME=${COPERNICUS_USERNAME} -e COPERNICUS_PASSWORD=${COPERNICUS_PASSWORD} -e DOWNLOADS_PATH=/mnt/files -v /mnt/files:/mnt/files ${DOCKER_IMAGE}"
echo $DOCKER_CMD_TEST >> /home/ubuntu/test_run.sh

DOCKER_CMD_TEST_REPEAT="sudo docker run -d \$@ -e ALLOW_REPEAT=TRUE -e DAYS_GAP=10 -e JUST_MAIN=TRUE -e DB_URL=${DB_URL} -e COPERNICUS_USERNAME=${COPERNICUS_USERNAME} -e COPERNICUS_PASSWORD=${COPERNICUS_PASSWORD} -e DOWNLOADS_PATH=/mnt/files -v /mnt/files:/mnt/files ${DOCKER_IMAGE}"
echo $DOCKER_CMD_TEST_REPEAT >> /home/ubuntu/test_run_repeat.sh


# Uncomment the following to run every day.
# crontab -l | { cat; echo "15 0 * * * $DOCKER_CMD"; } | crontab -
