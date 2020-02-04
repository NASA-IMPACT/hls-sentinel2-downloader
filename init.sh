#!/bin/sh

mkdir -p /code/downloads
aria2c --max-concurrent-downloads=15 \
       --max-connection-per-server=1 \
       --http-user=$COPERNICUS_USERNAME \
       --http-passwd=$COPERNICUS_PASSWORD  \
       --enable-rpc \
       --rpc-listen-all \
       --enable-rpc \
        --dir=$DOWNLOADS_PATH \
       -D


exec "$@"
