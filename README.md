# HLS Sentinel-2 Downloader (WIP)

This is a Python project to download Sentinel-2 files from ESA International Hub. 
It uses aria2c (https://aria2.github.io/) download utility to handle actual concurrent downloads


## Architecture Diagram
![Architecture](/images/downloader_architecture.png)

## Database Schema
![DatabaseSchema](/images/database_schema.png)


## Database Queries

* Compare total size of files to download vs uploaded per day
```sql
select T1.AvailableGB,T2.UploadedGB,T1.date from (select sum(size)/(1024*1024*1024) as "AvailableGB", CAST(beginposition as DATE) as "date" from granule where ignore_file=False  group by CAST(beginposition as DATE )) T1 JOIN (select sum(size)/(1024*1024*1024) as "UploadedGB", CAST(beginposition as DATE) as "date" from granule where uploaded=True  AND ignore_file=False  group by CAST(beginposition as DATE)) T2
where T1.date = T2.date;
```
![AvailableDownloadedSize](/images/available_vs_downloaded_size.png)

* Compare total number of files to download vs uploaded per day
```sql
select T1.Available,T2.Uploaded,T1.date from (select count(*) as "Available", CAST(beginposition as DATE) as "date" from granule where ignore_file=False  group by CAST(beginposition as DATE )) T1 JOIN (select count(*) as "Uploaded", CAST(beginposition as DATE) as "date" from granule where uploaded=True  AND ignore_file=False  group by CAST(beginposition as DATE)) T2
where T1.date = T2.date;
```
![AvailableDownloadedCount](/images/available_vs_downloaded_count.png)

* Get count and total size downloaded in last 10 minutes
```sql
select count(*) from granule where uploaded=True AND download_finished >= CONVERT_TZ( date_sub(now(),interval 10 minute), 'UTC', 'America/Chicago' )

select sum(size) / (1024 * 1024 * 1024) AS "Total Downloaded (GB)" from granule where uploaded=True AND download_finished >= CONVERT_TZ( date_sub(now(),interval 10 minute), 'UTC', 'America/Chicago' )

select CAST(beginposition AS DATE), count(*), sum(size) / (1024 * 1024 * 1024) AS "Total Downloaded (GB)" from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 10 minute), 'UTC', 'America/Chicago' ) group by CAST(beginposition AS DATE)

```
![DownloadedInLast10Min](/images/downloaded_in_last_10min.png)

* Get all the available links count per day in the database
```sql
select * from granule_count
```
![AvailableLinks](/images/available_links.png)

* Get 50 latest links form the database
```sql
select * from granule order by beginposition desc limit 50
```

* Check when the last time file was download or uploaded
```sql
select * from status
```

* Get the in progress downloads 
```sql
select * from granule where in_progress = True
```

* Get the total failed downloads 
```sql
select * from granule where download_failed = True
```

* Count the files to download for a day
```sql
select count(*) from granule where CAST(beginposition AS DATE) = '2020-05-30' AND ignore_file = False;
```

* Count the files that are uploaded
```sql
select count(*) from granule where CAST(beginposition AS DATE) = '2020-05-30' AND uploaded = True AND ignore_file = False;
```

* Get the failed downloads for a day
```sql
select count(*) from granule where CAST(beginposition AS DATE) = '2020-05-30' AND download_failed = True
```

* Count expired links by date
```sql
select count(*),CAST(beginposition as DATE) as start_date from granule where expired=true group by CAST(beginposition as DATE);
```

## Manual Installation Instructions

* Create a EC2 instance with atleast 32GB memory, 8 CPUs, 1 TB SSD
* Assign correct role to EC2 instance to write to S3 
* Create a MySQL database instance with atleast 8GB memory
* Put these EC2 and MySQL instances into its own VPC
* Add firewall rules to allows traffic from internet and your own laptop/desktop machine
* Create S3 buckets to store downloads and logs
* Copy the repository code inside EC2 instance
* Run install.sh inside EC2 instance which will install required system packages as well as aria2c (https://aria2.github.io/manual/en/html/README.html) which is used to download files from Sentinel International Access Hub(https://inthub.copernicus.eu/)
* Install python depedencies 
     sudo pip3 install -r requirements.txt 
* Create folder inside EC2 instance to temporarily store downloads and log files
* Copy settings_sample.ini to settings.ini and enter correct values
* Add execute permission on start.sh and stop.sh
     chmod +x start.sh
     chmod +x stop.sh
* Now run ./start.sh to start the downloader and ./stop.sh to stop the downloader


## Manual download test

It is possible to manually run the download of the files for testing using aria2c as below. Note set the valid values for username, password, downloads dir, and input urls text file

```
aria2c --max-concurrent-downloads=15 --split=1 --http-user=<username> --http-passwd=<password>  --dir=<downloads_dir> --allow-overwrite=true --input-file=<urls.txt> 
```

## Available Logs

Following logs are collected and uploaded to S3
* status logs: such as download is starting, file is downloaded, etc
* downloads logs: time of download, filename, size
* error logs: when file download or upload is failed, or any other error messages
* metrics logs: current available CPU/memory, number of active downloads and threads


## Future Tasks

* Investigate database performance tweaks
* Automate deployment
* Add tests
* Do the chaos engineering on the program
* Add debugging instructions for new developers
