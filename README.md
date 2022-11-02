# splunk-export
A parallel export script for moving splunk data. The export methods that are built into Splunk include web, command line (cli) and REST API. The challenge when moving large volumes of data is that these are all single threaded. If you could separate the data into two bins, then start the export using two separate cli exports, the process would go roughly twice as fast. This increase in performance by increasing the number of processes can continue until you exhaust the CPU resources of the search head or the CPU or I/O resources of the indexers. The goal of this utlity is to automate the parallelism of the export. 

The dimensions of export parallelism are index, sourcetype and time. The first step in the execution of this utlity is to "explode" these dimentions into separate partitions and write those to a file using a single process. Then, it forks n processes where n is a number you choose. Each of those processes then gets a lock on the partition file, selects the next un-processes partition, marks it as "in progress" and with it's process id and intiates a separate Splunk search to export the data. For example, if you specify one index, one sourcetype, and a 10 hour time range split by hour, the export will be divided into 10 partitions resulting in 10 separate export files. Increase that to two sourcetypes and the export will happen in 20 partitions. 

## Export Targets
- Mounted file system
- HTTP Event Collector (HEC)
- S3 (coming soon)

## Export Formats
- JSON
- gzipped JSON
- JSON over HEC
- CSV
- RAW
- Parquet (coming soon)

## Features
- Parallel export: Increase export performance by using available CPU resources
- Resume Failed: If something happens in the middle of an export job, you can restart it with the resume parameter. This will skip any partitions that completed, and only run those partitions that did not complete or were never started. 
- Incremental Export Mode: For each index and sourcetype the latest _time returned is stored in the partition file. On the next run, those latest _time values are retrieved and used as earliest _time for the searches and now() is used for the latest. This allows you to run it via cron and only pull in the events that were written since the last run. 

## Performance
Sample export with an index size of 12 GB containing 30 million events. 
- splunk cli export: 13m4s
- This utility with 4 processes: 3m28s
- This utility with 8 processes: 1m49s
- This utility with 12 processes: 1m18s

### htop of cli export
![htop cli export - single process](https://raw.githubusercontent.com/tmuth/splunk-export/main/images/htop-cli-export.png)

### htop of splunk-parallel-export.py with 12 processes
![htop of splunk-parallel-export.py with 12 processes](https://raw.githubusercontent.com/tmuth/splunk-export/main/images/htop-12-processes.png)

## Sample Output Structure
```
tmuth$ tree cloud1/
cloud1/
└── _internal
    ├── splunk_btool
    │   ├── _internal_splunk_btool_2022-11-01T00-00-00.json
    │   └── _internal_splunk_btool_2022-11-02T00-00-00.json
    ├── splunk_python
    │   ├── _internal_splunk_python_2022-11-01T00-00-00.json
    │   └── _internal_splunk_python_2022-11-02T00-00-00.json
    ├── splunkd
    │   ├── _internal_splunkd_2022-11-01T00-00-00.json
    │   └── _internal_splunkd_2022-11-02T00-00-00.json
    ├── splunkd_access
    │   ├── _internal_splunkd_access_2022-11-01T00-00-00.json
    │   └── _internal_splunkd_access_2022-11-02T00-00-00.json
    ├── splunkd_remote_searches
    │   ├── _internal_splunkd_remote_searches_2022-11-01T00-00-00.json
    │   └── _internal_splunkd_remote_searches_2022-11-02T00-00-00.json
    └── splunkd_ui_access
        ├── _internal_splunkd_ui_access_2022-11-01T00-00-00.json
        └── _internal_splunkd_ui_access_2022-11-02T00-00-00.json
  ```

