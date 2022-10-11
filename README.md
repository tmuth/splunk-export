# splunk-export
A parallel export script for moving splunk data. The export methods that are built into Splunk include web, command line (cli) and REST API. The challenge when moving large volumes of data is that these are all single threaded. If you could separate the data into two bins, then start the export using two separate cli exports, the process would go roughly twice as fast. This increase in performance by increasing the number of processes can continue until you exhaust the CPU resources of the search head or the CPU or I/O resources of the indexers. The goal of this utlity is to automate the parallelism of the export. 

The dimensions of export parallelism are index, sourcetype and time. The first step in the execution of this utlity is to "explode" these dimentions into separate partitions and write those to a file using a single process. Then, it forks n processes where n is a number you choose. Each of those processes then gets a lock on the partition file, selects the next un-processes partition, marks it as "in progress" and with it's process id and intiates a separate Splunk search to export the data. For example, if you specify one index, one sourcetype, and a 10 hour time range split by hour, the export will be divided into 10 partitions resulting in 10 separate export files. Increase that to two sourcetypes and the export will happen in 20 partitions. 

## Export Targets
- Mounted file system
- HTTP Event Collector (HEC)
- S3 (coming soon)

