# HLS Sentinel-2 Downloader (WIP/TODO)

This is a Python project to download Sentinel-2 files from ESA International Hub. 
It uses aria2c (https://aria2.github.io/) download utility to handle actual downloads

# Manual Installation Instructions

* Create a EC2 instance with atleast 32GB memory, 8 CPUs, 1 TB SSD
* Assign correct role to EC2 instance to write to S3 
* Create a MySQL database instance with atleast 8GB memory
* Put these EC2 and MySQL instances into its own VPC
* Add firewall rules to allows traffic from internet and your own laptop/desktop machine
* Create S3 buckets to store downloads and logs
* Copy the repository code inside EC2 instance
* Run install.sh inside EC2 instance
* Install python depedencies 
     sudo pip3 install -r requirements.txt 
* Create folder inside EC2 instance to temporarily store downloads and log files
* Copy settings_sample.ini to settings.ini and enter correct values
* Add execute permission on start.sh and stop.sh
     chmod +x start.sh
     chmod +x stop.sh
* Now run ./start.sh


# Database Queries


Get 50 latest links form the database
```sql
select * from granule order by beginposition desc limit 50
```

Check when the last time file was download or uploaded
```sql
select * from status
```

Get all the available links count per day in the database
```sql
select * from granule_count
```

Get the in progress downloads 
```sql
select * from granule where in_progress = True
```

Get the total failed downloads 
```sql
select * from granule where download_failed = True
```

Count the files to download for a day
```sql
select count(*) from granule where CAST(beginposition AS DATE) = '2020-05-30' AND ignore_file = False;
```
Count the files that are uploaded
```sql
select count(*) from granule where CAST(beginposition AS DATE) = '2020-05-30' AND uploaded = True AND ignore_file = False;
```

Get the failed downloads for a day
```sql
select count(*) from granule where CAST(beginposition AS DATE) = '2020-05-30' AND download_failed = True
```

# Manual download test

It is possible to manually run the download of the files for testing using aria2 as below. Note set the valid values for username, password, downloads dir, and input urls text file

```
aria2c --max-concurrent-downloads=15 --split=1 --http-user=<username> --http-passwd=<password>  --dir=<downloads_dir> --allow-overwrite=true --input-file=<urls.txt> 
```

# Available Logs

Following logs are correct
* status logs: such as download is starting 
* downloads logs: time of download, filename, size
* error logs: when file download or upload is failed, or any other error messages
* metrics logs: current available CPU/memory, number of active downloads and threads


# Future Tasks

* Add correct indexes http://docs.peewee-orm.com/en/latest/peewee/models.html#indexes-and-constraints
* Automate deployment
* Add tests
* Add debugging instructions
* Add screenshots to the readme