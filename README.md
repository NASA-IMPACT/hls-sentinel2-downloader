# HLS Sentinel2 Downloader

A self-deployable application to run on cloud that parallelly fetches Sentinel-2 data from the ESA international hub and uploads them to S3.


## Deployment

First copy the file `terraform/conf.auto.tfvars.example` to `terraform/conf.auto.tfvars` and fill in the necessary values. You need to provide the Copenicus username and password as well as the public key for the ssh-key with which you want to deploy the EC2 instance. You can also modify the database settings as you like.

After that, you are ready to deploy:

```bash
# From the root folder:
./deploy.sh
```

Deployment happens in several stages:

* First an ECR repository is created in the cloud. The docker image of the whole
  repo is created and pushed to this ECR repository.
* Next, the S3 bucket to store the AWS lambda functions are deployed.
* Finally, the whole stack is deployed to the cloud.


## Running the downloader

By default, the default date for the downloader is three days ago from the start date. Once all granules for the default date are downloaded, the downloader can optionally start downloading missed/failed granules for all 15 days before the default date. If the downloader runs for more than a day, it is automatically shut down.

Once deployed, the EC2 instance is setup with the docker image capable of downloading Sentinel-2 granules from the Copernicus API.

You can ssh into the EC2 instance with your private ssh-key. In the home folder of the instance, three example scripts are setup for you to run the downloader.

```bash
# Run and output to the default S3 bucket.
# By default, this downloads for the default date and all 15 days before it
# and automatically stops at the end of the day.
bash run_docker.sh

# Test run to download 100 granules from 10 days ago. Also lets us specify
# our own bucket to download to.
bash test_run.sh -e UPLOAD_BUCKET=output_bucket

# Test run but this time download 1000 granules and
# allows granules that have already been downloaded to be downloaded again.
bash test_run_repeat.sh -e UPLOAD_BUCKET=output_bucket_name -e MAX_DOWNLOADS=1000
```

Modify one of the above scripts to customize the downloader. All scripts are of the following form:

```bash
sudo docker run -d -e DOWNLOADS_PATH=/mnt/files -v /mnt/files:/mnt/files <DOCKER_IMAGE>
```

A bunch of environment variables can be set:

```
# Required fields:
DB_URL: Endpoint of the database used for logging.
COPERNICUS_USERNAME: Username to log in to Copernicus API.
COPERNICUS_PASSWORD: Password to log in to Copernicus API.
UPLOAD_BUCKET: Bucket to put downloaded granules into.

# Other fields:
MAX_DOWNLOADS=n: Maximum number of granules to download.
ALLOW_REPEAT=TRUE: Allows granules to be re-downloaded even if they have already been downloaded once.
DAYS_GAP=n: The default date is this many days ago from today. Default value = 3.
JUST_MAIN=TRUE: Download only for the default date. If unset, missed or failed granules for all 15 days before the default date are also downloaded.
```


## Viewing logs

You can connect to the RDS instance from inside the VPC (for example, you can use the EC2 instance created above to connect using a postgres client).

Some common SQL queries that you can perform to query the logs:

```sql
-- View logs for 2020 May 10
SELECT * FROM job_log WHERE date(logged_at) == '2020-05-10';

-- Find the job that downloaded granules for 2020-03-07
SELECT * FROM job WHERE date(date_handled) == '2020-05-07';

-- Find the granules downloaded on 2020-05-10
SELECT * FROM granule WHERE date(downloaded_at) == '2020-05-10';

-- Find the logs and granules for a particular job.
SELECT * FROM job_log WHERE job_id == <job_id>;
SELECT * FROM granule WHERE downloader_job_id == <job_id>;
```
