#Following are useful queries that are to be run manually for testing/debugging/metrics

#add new column
ALTER TABLE granule ADD COLUMN expired boolean NOT NULL DEFAULT false;

#find expired links by date
select count(*),CAST(beginposition as DATE) as start_date from granule where expired=true group by CAST(beginposition as DATE);

#find NOT expired links by date
select count(*),CAST(beginposition as DATE) as start_date from granule where expired=false group by CAST(beginposition as DATE);

#expire links older than 21 days
update granule set expired=false  where beginposition <= CONVERT_TZ(date_sub(now(),interval 21 day)

#unexpire links older than given days
update granule set expired=false  where beginposition > CONVERT_TZ(date_sub(now(),interval 10 day), 'UTC', 'America/Chicago' )

#find  unexpired links older than 21 days
select * from granule where expired=false and beginposition > CONVERT_TZ(date_sub(now(),interval 21 day), 'UTC', 'America/Chicago' )

#find  unexpired links older than 21 days, show grouped by date
select count(*), CAST(beginposition as DATE)  from granule where expired=false and beginposition > CONVERT_TZ(date_sub(now(),interval 21 day), 'UTC', 'America/Chicago' ) group by CAST(beginposition as DATE);

#count files by date
select count(*) from granule where CAST(beginposition as DATE) = '2020-06-03'

#get files by date
select * from granule where CAST(beginposition as DATE) = '2020-08-04'

#get files by date which are not uploaded and which are not expired
select * from granule where CAST(beginposition as DATE) = '2020-10-30' and ignore_file = False and uploaded= FALSE and expired = False

#get files which are still in progress from last 2 days, their in_progress flag needs to be reset
select CAST(beginposition as DATE), count(*) from granule where ignore_file = False and in_progress = True and download_started <= CONVERT_TZ(date_sub(now(),interval 2 day), 'UTC', 'America/Chicago' ) group by CAST(beginposition as DATE)

#reset the in_progress flag of orphan downloads
update granule set in_progress = FALSE where ignore_file = False and in_progress = True and download_started <= CONVERT_TZ(date_sub(now(),interval 2 day), 'UTC', 'America/Chicago' )

#group files by date
select count(*) from granule group by CAST(beginposition as DATE) ;

#find not uploaded files
select * from granule where uploaded = False and ignore_file =False and  CAST(beginposition as DATE) = '2020-10-11';

#to find granules where start date <> end date
select *
from (
         select CAST(beginposition as DATE) as start_date, CAST(endposition as DATE) as end_date
         from granule) innerTable
where start_date <> end_date;

#for export
select filename,download_url,beginposition from granule where CAST(beginposition as DATE) = '2020-06-15' limit 100

#get size downloaded per day
select sum(size)/(1024*1024*1024) as "Downloads (GB)", CAST(download_finished as DATE ) from granule group by CAST(download_finished as DATE )

#to find days where available == uploaded (most used query)
select T1.Available,T2.Uploaded,T1.date from (select count(*) as "Available", CAST(beginposition as DATE) as "date" from granule where ignore_file=False  group by CAST(beginposition as DATE )) T1 JOIN (select count(*) as "Uploaded", CAST(beginposition as DATE) as "date" from granule where uploaded=True  AND ignore_file=False  group by CAST(beginposition as DATE)) T2
where T1.date = T2.date;

#find available size vs downloaded size
select T1.AvailableGB,T2.UploadedGB,T1.date from (select sum(size)/(1024*1024*1024) as "AvailableGB", CAST(beginposition as DATE) as "date" from granule where ignore_file=False  group by CAST(beginposition as DATE )) T1 JOIN (select sum(size)/(1024*1024*1024) as "UploadedGB", CAST(beginposition as DATE) as "date" from granule where uploaded=True  AND ignore_file=False  group by CAST(beginposition as DATE)) T2
where T1.date = T2.date;

#Get all the available links count per day in the database
select * from granule_count

#Get count of all the available links
select count(*) from granule

#find data downloaded in last 10 minutes
select CAST(beginposition AS DATE), count(*), sum(size) / (1024 * 1024 * 1024) AS "Total Downloaded (GB)" from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 10 minute), 'UTC', 'America/Chicago' ) group by CAST(beginposition AS DATE)

#find data downloaded in last 1 hour
select CAST(beginposition AS DATE), count(*), sum(size) / (1024 * 1024 * 1024) AS "Total Downloaded (GB)" from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 1 hour), 'UTC', 'America/Chicago' ) group by CAST(beginposition AS DATE)

#find data downloaded in last 12 hours
select CAST(beginposition AS DATE), count(*), sum(size) / (1024 * 1024 * 1024) AS "Total Downloaded (GB)" from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 12 hour), 'UTC', 'America/Chicago' ) group by CAST(beginposition AS DATE)

#find data downloaded in last 24 hours
select CAST(beginposition AS DATE), count(*), sum(size) / (1024 * 1024 * 1024) AS "Total Downloaded (GB)" from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 24 hour), 'UTC', 'America/Chicago' ) group by CAST(beginposition AS DATE)

#find max, min, avg download time of files downloaded in last 10 days
select  max(TIME_TO_SEC(TIMEDIFF(download_finished,download_started)))/60 as "Max Download Time (minutes)", min(TIME_TO_SEC(TIMEDIFF(download_finished,download_started)))/60 as "Min Download Time (minutes)", avg(TIME_TO_SEC(TIMEDIFF(download_finished,download_started)))/60 as "Avg Download Time (minutes)"  from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 10 day), 'UTC', 'America/Chicago' );

#export download urls
select download_url,filename,checksum from granule order by beginposition desc limit 60000

#list files and their size downloaded in last 24 hours
select CAST(download_finished AS DATETIME), filename, size / (1024 * 1024 * 1024) AS "(GB)"  from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 24 hour), 'UTC', 'America/Chicago' ) order by CAST(download_finished AS DATETIME) asc

#count files downloaded in last 1 hour
select count(filename) from granule where uploaded=True AND download_finished >= CONVERT_TZ(date_sub(now(),interval 1 hour), 'UTC', 'America/Chicago' ) order by CAST(download_finished AS DATETIME) asc

#find database size
SELECT table_schema, ROUND(SUM(data_length+index_length)/1024/1024/1024,2) "size in GB" FROM information_schema.tables GROUP BY 1 ORDER BY 2 DESC;

#find a granule by name
select * from granule where filename LIKE "%S2B_MSIL1C_20201003T220539_N0209_R072_T04VCK_20201003T223152%"

#find granules with download urls more than 5 days old not yet uploaded
select *, CAST(beginposition as DATE)  from granule where expired=false and ignore_file=false and uploaded=false and beginposition > CONVERT_TZ(date_sub(now(),interval 21 day), 'UTC', 'America/Chicago' ) and beginposition < CONVERT_TZ(date_sub(now(),interval 5 day), 'UTC', 'America/Chicago' ) order by CAST(ingestiondate as DATE);
