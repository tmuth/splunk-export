#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import
from __future__ import print_function
import time
from datetime import datetime, timedelta
from pprint import pprint
import dateutil.parser
import json
import re
import os
import tempfile
import logging
#from splunk_http_event_collector import http_event_collector
import timeout_decorator
import configparser

import splunklib.client as client
import splunklib.results as results
import sys
from time import sleep
import multiprocessing


# pip install configparser,dateutil,splunk-sdk,splunk-hec-ftf


if len(sys.argv) < 2:
    print("Pass the name of a config file as argument 1")
    exit(1)

if not os.path.exists(sys.argv[1]):
    print("Cannot find the configuration file: "+sys.argv[1])
    exit(1)
#config_file='export1.conf'
config_file=sys.argv[1]

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

logger = logging.getLogger()
logger.handlers[0].stream = sys.stdout
logger.setLevel(logging.DEBUG) # DEBUG,INFO,WARNING,ERROR,CRITICAL


def load_config():
    global config
    config = configparser.ConfigParser()
    config.read(config_file)

def create_output_dir():
    path=config.get('export', 'directory')
    if not os.path.exists(path):
        path_new=os.path.normpath(path)
        os.makedirs(path_new)

def build_search_string(partition_in):
    logging.info('build_search_string-start')
    logging.debug('indexes: %s',config.get('search', 'indexes'))
    logging.debug('extra: %s',config.get('search', 'extra'))
    s='search index='+partition_in["index"]
    s+=' '+config.get('search', 'extra')
    
    logging.debug('s: %s',s)
    logging.info('build_search_string-end')
    return s

def explode_date_range(begin_date_in: str,end_date_in: str,interval_unit_in: str,interval_in: int):
    logging.info('explode_date_range-start')
    logging.debug('begin_date_in: %s',begin_date_in)
    logging.debug('end_date_in: %s',end_date_in)
    begin_date = dateutil.parser.parse(begin_date_in)
    end_date = dateutil.parser.parse(end_date_in)

    begin_current=begin_date
    result = []
    
    while begin_current < end_date:
        end_current = begin_current+timedelta(**{interval_unit_in: interval_in})-timedelta(seconds=1)
        result.append ([begin_current,end_current])
        begin_current=end_current+timedelta(seconds=1)
    logging.info('explode_date_range-end')
    return result

def write_search_partitions(date_array_in):
    logging.info('write_search_partitions-start')
    index_list=config.get('search', 'indexes').split(",")
    json_data = {}
    result_list = []
    i=0
    for index_entry in index_list:
        for entry in date_array_in:
            i+=1
            search_partition={'id':i,'index':index_entry,
                'earliest': entry[0].isoformat(),'latest':entry[1].isoformat(),
                #'earliest': entry[0].strftime("%m/%d/%Y:%H:%M:%S"),'latest':entry[1].strftime("%m/%d/%Y:%H:%M:%S"),
                             'status':'not started','pid':''}
            result_list.append(search_partition)
    
    summary_data={'partition_count': i,
                  'complete_count': 0,
                  'status': 'starting',
                  'start_time': datetime.now().isoformat(),
                  'end_time': '',
                  'total_seconds': ''}
    
    json_data['summary_data']=summary_data
    json_data['partitions']=result_list
    
    search_partitions=json.dumps(json_data, indent=2, sort_keys=False)
    #print(search_partitions)      
    
    
    with open(config.get('export', 'partition_file_name'), "w") as outfile:
        outfile.write(search_partitions)
        
    logging.info('write_search_partitions-end')

def update_partition_status(partition_file_in,partition_in,status_in,lock_in):
    lock_in.acquire()
    with open(partition_file_in,'r+') as f:
        #portalocker.lock(f, portalocker.LOCK_EX)
        data = json.load(f)
        search_partition_out=None
        for search_partition in data["partitions"]:
            if search_partition["id"]==partition_in["id"]:
                #pprint(search_partition["earliest"])
                search_partition["status"]=status_in
                #return search_partition
                break
                
        if status_in == 'completed':
            data["summary_data"]["complete_count"]=int(data["summary_data"]["complete_count"])+1
            
        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()
    lock_in.release()

def finalize_partition_status(partition_file_in,lock_in):
    lock_in.acquire()
    with open(partition_file_in,'r+') as f:
        #portalocker.lock(f, portalocker.LOCK_EX)
        data = json.load(f)
        data["summary_data"]["end_time"]=datetime.now().isoformat()
        date_start=datetime.fromisoformat(data["summary_data"]["start_time"])
        date_end=datetime.fromisoformat(data["summary_data"]["end_time"])
        data["summary_data"]["total_seconds"] = round((date_end-date_start).total_seconds(),1)
        logging.info('Total seconds: %s',data["summary_data"]["total_seconds"])
        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()
    lock_in.release()
        
def get_search_partition(partition_file_in,lock_in):
    lock_in.acquire()
    with open(partition_file_in,'r+') as f:
        
        #portalocker.lock(f, portalocker.LOCK_EX)
        data = json.load(f)
        search_partition_out=None
        for search_partition in data["partitions"]:
            if search_partition["status"]=='not started':
                #pprint(search_partition["earliest"])
                search_partition["status"]='assigned'
                search_partition["pid"]=os.getpid()
                search_partition_out=search_partition
                #return search_partition
                break
                #pid = os.getpid()
        #with open("sample.json", "w") as outfile:
        #outfile.write(json_object)
        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()
        
    lock_in.release()
    return search_partition_out
        #f.write(json_object)
        #pprint(data)

        


def search_export(service_in,search_in,partition_in):
    logging.info('search_export-start')

    logging.debug(service_in)
    kwargs_export = {"search_mode": "normal",
                     'earliest_time': partition_in["earliest"],
                     'latest_time': partition_in["latest"],
                     "output_mode": "json"}
    job = service_in.jobs.export(search_in, **kwargs_export)

    logging.info("search_export-end")
    return job
        
def dispatch_searches(partition_file_in,config_in,lock_in):
    logging.info('dispatch_searches-start')
    global config
    config=config_in
    while True:
        partition_out=get_search_partition(partition_file_in,lock_in)

        if partition_out is not None:
            search_string=build_search_string(partition_out)
            service=connect()
            job=search_export(service,search_string,partition_out)
            #print_results(job)
            write_results(job,partition_out)
            update_partition_status(partition_file_in,partition_out,'completed',lock_in)
            #job.cancel()
        else:
            break

    logging.info('dispatch_searches-end')

        
def write_results(job_in,partition_in):
    logging.info('write_results-start')
    earliest=partition_in["earliest"]
    earliest=re.sub("[/:]", "-", earliest)

    output_file=config.get('export', 'directory')+'/'+partition_in["index"]+"_"+earliest+".json"
    output_file=os.path.normpath(output_file)
    f = open(output_file, "w")
    reader = results.JSONResultsReader(job_in)
    for result in reader:
        if isinstance(result, dict):
            print(result,file=f)
        elif isinstance(result, results.Message):
            # Diagnostic messages may be returned in the results
            print(result,file=f)
    
    f.close()
    logging.info('write_results-end')

        
def connect():
    try:
        logging.info('connect-start')
        logging.debug('SPLUNK_HOST: %s',config.get('splunk', 'SPLUNK_HOST'))
        logging.debug('SPLUNK_PORT: %s',config.get('splunk', 'SPLUNK_PORT'))
        logging.debug('SPLUNK_AUTH_TOKEN: %s',config.get('splunk', 'SPLUNK_AUTH_TOKEN'))
       
        service = client.connect(
            host=config.get('splunk', 'SPLUNK_HOST'),
            port=config.get('splunk', 'SPLUNK_PORT'),
        #    username=USERNAME,
        #    password=PASSWORD)
            splunkToken=config.get('splunk', 'SPLUNK_AUTH_TOKEN'),
            autologin=True)
        logging.debug(service)
        logging.info('connect-successful')
        logging.info('connect-end')
        return service
    except:
        logging.error('connect-failed')

def main():
   
    
    load_config()
    partition_file=config.get('export', 'partition_file_name')
    service=connect()
    logging.debug(service)
    date_array=explode_date_range(config.get('search', 'begin_date'),config.get('search', 'end_date'),
                              config.get('export', 'parition_units'),int(config.get('export', 'partition_interval')))
    write_search_partitions(date_array)
    create_output_dir()
    #get_search_partition(partition_file)

    procs = int(config.get('export', 'parallel_processes'))   # Number of processes to create
    lock = multiprocessing.Lock()
	# Create a list of jobs and then iterate through
	# the number of processes appending each process to
	# the job list
    jobs = []
    for i in range(0, procs):
        process = multiprocessing.Process(target=dispatch_searches,args=((partition_file,config,lock)))
        jobs.append(process)


	# Start the processes (i.e. calculate the random number lists)
    for j in jobs:
        j.start()

	# Ensure all of the processes have finished
    for j in jobs:
        j.join()
    #dispatch_searches(partition_file)
    finalize_partition_status(partition_file,lock)

if __name__ == "__main__":
    main()

