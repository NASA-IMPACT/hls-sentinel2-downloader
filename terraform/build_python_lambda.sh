#!/bin/sh

terraform_workspace="$(terraform workspace list | grep '*' | cut -d' ' -f2-)"
lambda_bucket="${terraform_workspace}-lambda"

db_path="$(cd "$(dirname "../src/db")"; pwd)/$(basename "../src/db")"
# lib_path="$(cd "$(dirname "../lib")"; pwd)/$(basename "../lib")"
# common_path="$(cd "$(dirname "../src/common")"; pwd)/$(basename "../src/common")"

output_path="$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"
input_path="$(cd "$(dirname "$2")"; pwd)/$(basename "$2")"

if [ ! -d "$input_path/v-env" ]; then
  virtualenv $input_path/v-env
fi

. $input_path/v-env/bin/activate
pip install -r $input_path/requirements.txt

cd $input_path/v-env/lib/python*/site-packages
zip -r9 -FS $output_path . -x __pycache__\/*

cd $input_path
zip -r -g $output_path ./* -x v-env/\* -x __pycache__\/*

cd $db_path
zip -r -g $output_path ./* -x __pycache__\/*

# cd $lib_path
# zip -r -g $output_path ./* -x __pycache__\/*
#
# cd $common_path
# cd ..
# zip -r -g $output_path ./common -x __pycache__\/*

aws s3 cp $output_path s3://$lambda_bucket
