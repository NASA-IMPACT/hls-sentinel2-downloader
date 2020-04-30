# HLS Sentinel2 Downloader

A self-deployable application to run on cloud that parallelly fetches Sentinel-2 data from the ESA international hub and uploads them to S3.


## Deploy Instructions

 # TODO Add instructions to create workspace for terraform or use variable PROJECT_PREFIX

First copy the file `terraform/conf.auto.tfvars.example` to `terraform/conf.auto.tfvars` and fill in the necessary values. You need to provide the Copenicus username and password as well as the public key for the ssh-key with which you want to deploy the EC2 instance. You can also modify the database settings as you like.

After that, you are ready to deploy:

```bash
# From the root folder:
$ ./deploy.sh
```

Deployment happens in several stages:

* First an ECR repository is created in the cloud. The docker image of the whole
  repo is created and pushed to this ECR repository.
* Next, the S3 bucket to store the AWS lambda functions are deployed.
* Finally, the whole stack is deployed to the cloud.


## Test Instructions

TODO
