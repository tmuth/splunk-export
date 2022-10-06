#!/usr/bin/env python
# coding: utf-8
from __future__ import absolute_import
from __future__ import print_function
from contextlib import nullcontext
import time
from datetime import datetime, timedelta
from pprint import pprint
import dateutil.parser
import json,shutil
import re
import os
import tempfile
import logging
#from splunk_http_event_collector import http_event_collector
import timeout_decorator
import configparser
import gzip
import itertools

import splunklib.client as client
import splunklib.results as results
import sys
from time import sleep
import multiprocessing
from splunk_hec import splunk_hec


# pip install configparser,dateutil,splunk-sdk,splunk-hec-ftf


if len(sys.argv) < 2:
    print("Pass the name of a config file as argument 1")
    exit(1)

if not os.path.exists(sys.argv[1]):
    print("Cannot find the configuration file: "+sys.argv[1])
    exit(1)
#config_file='export1.conf'
config_file=sys.argv[1]





def set_logging_level():
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

    logger = logging.getLogger()
    logger.handlers[0].stream = sys.stdout
    log_level_config = config.get('export', 'log_level').upper()
    log_level_config=re.sub(r"([A-Z]+).*", r"\1", log_level_config)
    print(log_level_config)
    level = logging.getLevelName(log_level_config) #
    #logger.setLevel(logging.INFO) # DEBUG,INFO,WARNING,ERROR,CRITICAL
    logger.setLevel(level)
    print(logger.getEffectiveLevel())

def load_config():
    global config
    config = configparser.ConfigParser(inline_comment_prefixes=('#',';'))
    config.read(config_file)

def create_output_dir(path_in):
    if not os.path.exists(path_in):
        path_new=os.path.normpath(path_in)
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
    if not end_date_in:
        end_date=datetime.now()
    else:
        end_date = dateutil.parser.parse(end_date_in)

    begin_current=begin_date
    result = []
    
    while begin_current < end_date:
        
        #end_current = begin_current+timedelta(**{interval_unit_in: interval_in})-timedelta(seconds=1)
        end_current = begin_current+timedelta(**{interval_unit_in: interval_in})
        if end_current > end_date:
            end_current = end_date
        logging.debug('end_current: %s',end_current)
        result.append ([begin_current,end_current])
        #begin_current=end_current+timedelta(seconds=1)
       
        
        begin_current=end_current
        logging.debug('begin_current: %s',begin_current)
    logging.info('explode_date_range-end')
    return result

def get_index_sourcetype_array():
    index_count=0
    sourcetype_count=0
    if not config.get('search', 'sourcetypes'):
        out_array=config.get('search', 'indexes').split(",")
        index_count=len(out_array)
    else:
        index_list=config.get('search', 'indexes').split(",")
        sourcetype_list=config.get('search', 'sourcetypes').split(",")
        out_array = itertools.product(index_list, sourcetype_list)
        index_count=len(index_list)
        sourcetype_count=len(sourcetype_list)

    return out_array,index_count,sourcetype_count

def write_resume_summary(partition_file_in):
    with open(partition_file_in,'r+') as f:
        data = json.load(f)
        data["summary_data"]["start_time"]=datetime.now().isoformat()
        data["summary_data"]["status"] = 'resume'

        for search_partition in data["partitions"]:
            if search_partition["status"]!='complete':
                search_partition["status"]='not started'
                search_partition["pid"]=''

        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()


def cleanup_failed_run(partition_file_in):
    logging.info('cleanup_failed_run-start')
    if not os.path.isfile(partition_file_in):
        return False
    else:
        data={}
        with open(partition_file_in,'r') as f:
            data = json.load(f)

        logging.info('status: %s',data["summary_data"]["status"])
        logging.info('resume_mode: %s',config.get('export', 'resume_mode'))
        if data["summary_data"]["status"]!='complete' and config.get('export', 'resume_mode')=='resume':
            backup_file=partition_file_in+'bak'
            shutil.copy(partition_file_in, backup_file)
            write_resume_summary(partition_file_in)
            logging.info('cleanup_failed_run-ok to resume')
            return True
        else:
            logging.info('cleanup_failed_run-do not resume')
            return False

def write_search_partitions(date_array_in):
    logging.info('write_search_partitions-start')
    index_sourcetype_array,index_count,source_type_count=get_index_sourcetype_array()
    json_data = {}
    result_list = []
    i=0
    for index_st_entry in index_sourcetype_array:
        for entry in date_array_in:
            i+=1
            
            search_partition={'id':i,
                'earliest': entry[0].isoformat(),'latest':entry[1].isoformat(),
                             'status':'not started','result_count':'','pid':''}

            sourcetype_str=''
            if type(index_st_entry) == tuple: 
                search_partition['index']=index_st_entry[0]
                search_partition['sourcetype']=index_st_entry[1]
            else:
                search_partition['index']=index_st_entry

            result_list.append(search_partition)
    
    summary_data={'partition_count': i,
                  'complete_count': 0,
                  'status': 'starting',
                  'start_time': datetime.now().isoformat(),
                  'end_time': '',
                  'indexes':index_count,
                  'total_seconds': '',
                  'total_results': '0'}

    if source_type_count>0:
        summary_data['sourcetypes']=source_type_count
    
    json_data['summary_data']=summary_data
    json_data['partitions']=result_list
    
    search_partitions=json.dumps(json_data, indent=2, sort_keys=False)
    #print(search_partitions)      
    
    
    with open(config.get('export', 'partition_file_name'), "w") as outfile:
        outfile.write(search_partitions)
        
    logging.info('write_search_partitions-end')

def update_partition_status(partition_file_in,partition_in,status_in,lock_in,result_count_in):
    logging.info('update_partition_status-start')
    logging.info('result_count_in: %s',result_count_in)
    lock_in.acquire()
    with open(partition_file_in,'r+') as f:
        #portalocker.lock(f, portalocker.LOCK_EX)
        data = json.load(f)
        search_partition_out=None
        for search_partition in data["partitions"]:
            if search_partition["id"]==partition_in["id"]:
                #pprint(search_partition["earliest"])
                search_partition["status"]=status_in
                search_partition["result_count"]=result_count_in
                #return search_partition
                break
                
        if status_in == 'complete':
            data["summary_data"]["complete_count"]=int(data["summary_data"]["complete_count"])+1
            data["summary_data"]["total_results"]=int(data["summary_data"]["total_results"])+int(result_count_in)
            
            
        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()
    lock_in.release()
    logging.info('update_partition_status-end')

def finalize_partition_status(partition_file_in,lock_in):
    lock_in.acquire()
    with open(partition_file_in,'r+') as f:
        #portalocker.lock(f, portalocker.LOCK_EX)
        data = json.load(f)
        data["summary_data"]["end_time"]=datetime.now().isoformat()
        date_start=datetime.fromisoformat(data["summary_data"]["start_time"])
        date_end=datetime.fromisoformat(data["summary_data"]["end_time"])
        data["summary_data"]["status"] = 'complete'
        data["summary_data"]["total_seconds"] = round((date_end-date_start).total_seconds(),1)
        logging.info('Total seconds: %s',data["summary_data"]["total_seconds"])
        logging.info('Total results: %s',data["summary_data"]["total_results"])
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
            result_count=write_results(job,partition_out)
            update_partition_status(partition_file_in,partition_out,'complete',lock_in,result_count)
            #job.cancel()
        else:
            break

    logging.info('dispatch_searches-end')


def write_results(job_in,partition_in):
    if config.get('export', 'output_destination')=='file':
        return write_results_to_file(job_in,partition_in)

    if config.get('export', 'output_destination')=='hec':
        return send_results_to_hec(job_in,partition_in)

def send_results_to_hec(job_in,partition_in):
    hec_server=config.get('splunk_target', 'HEC_HOST')
    hec_port=config.get('splunk_target', 'HEC_PORT')
    hec_token=config.get('splunk_target', 'HEC_TOKEN')
    use_hec_tls=config.get('splunk_target', 'HEC_TLS')
    hec_tls_verify=config.get('splunk_target', 'HEC_TLS_VERIFY')

    # Create an object reference to the library, initalized with our settings.
    splhec = splunk_hec( token=hec_token, hec_server=hec_server, hec_port=hec_port,use_hec_tls=use_hec_tls,hec_tls_verify=hec_tls_verify )

    index = 'hec_test'
    sourcetype = '_json'
    source = 'hec:test:events'
    input_type='json'
    
    payload = {}
    try:
        reader = results.JSONResultsReader(job_in)
        i=0
        for result in reader:
            
            i+=1
            if isinstance(result, dict):
                payload['event']=str(result["_raw"])
                payload['time'] = result["_time"]
                payload['index'] = index
                payload['sourcetype'] = sourcetype
                splhec.send_event(payload)
            elif isinstance(result, results.Message):
                # Diagnostic messages may be returned in the results
                logging.info('result: %s',result)
    finally:
        logging.debug("Result count: %s",i)
        splhec.stop_threads_and_processing()
        return i


def write_results_to_file(job_in,partition_in):
    logging.info('write_results-start')
    
    earliest=partition_in["earliest"]
    earliest=re.sub("[/:]", "-", earliest)
    file_path=config.get('export', 'directory')+'/'+partition_in["index"]
    create_output_dir(file_path)

   # if partition_in["sourcetype"]:
    if "sourcetype" in partition_in:
        file_path=config.get('export', 'directory')+'/'+partition_in["index"]+'/'+partition_in["sourcetype"]
        create_output_dir(file_path)
        file_name=file_path+"/"+partition_in["index"]+"_"+partition_in["sourcetype"]+"_"+earliest
    else:
        file_name=file_path+"/"+partition_in["index"]+"_"+earliest

    output_file_temp=file_name+".tmp"
    output_file_temp=os.path.normpath(output_file_temp)
    output_file=file_name+".json"
    output_file=os.path.normpath(output_file)

    if config.get('export', 'gzip')=='true':
        f = gzip.open(output_file_temp, compresslevel=9, mode='wt')
        output_file=output_file+'.gz'
    else:
        f = open(output_file_temp, "w")
    #f = gzip.open(output_file_temp, 'wt')
    #f = tempfile.mkstemp(dir=config.get('export', 'directory'))

    try:
        reader = results.JSONResultsReader(job_in)
        i=0
        for result in reader:
            
            i+=1
            if isinstance(result, dict):
                print(result,file=f)
            elif isinstance(result, results.Message):
                # Diagnostic messages may be returned in the results
                print(result,file=f)
    finally:
        logging.debug("Result count: %s",i)
        
        os.rename(output_file_temp,output_file)
        f.close()
        return(i)

    
    
    
    #f.close()
    logging.info('write_results-end')

        
def connect():
    try:
        logging.info('connect-start')
        logging.debug('SPLUNK_HOST: %s',config.get('splunk_source', 'SPLUNK_HOST'))
        logging.debug('SPLUNK_PORT: %s',config.get('splunk_source', 'SPLUNK_PORT'))
        logging.debug('SPLUNK_AUTH_TOKEN: %s',config.get('splunk_source', 'SPLUNK_AUTH_TOKEN'))
       
        service = client.connect(
            host=config.get('splunk_source', 'SPLUNK_HOST'),
            port=config.get('splunk_source', 'SPLUNK_PORT'),
            splunkToken=config.get('splunk_source', 'SPLUNK_AUTH_TOKEN'),
            autologin=True)
        logging.debug(service)
        logging.info('connect-successful')
        logging.info('connect-end')
        return service
    except:
        logging.error('connect-failed')

def main():
   
    load_config()
    set_logging_level()
    partition_file=config.get('export', 'partition_file_name')

    should_resume=cleanup_failed_run(partition_file)

    if not should_resume:
        date_array=explode_date_range(config.get('search', 'begin_date'),config.get('search', 'end_date'),
                                config.get('export', 'parition_units'),int(config.get('export', 'partition_interval')))
        write_search_partitions(date_array)
        create_output_dir(config.get('export', 'directory'))
    

    procs = int(config.get('export', 'parallel_processes'))   # Number of processes to create
    lock = multiprocessing.Lock()
    jobs = []
    for i in range(0, procs):
        process = multiprocessing.Process(target=dispatch_searches,args=((partition_file,config,lock)))
        jobs.append(process)

    for j in jobs:
        j.start()

	# Ensure all of the processes have finished
    for j in jobs:
        j.join()
    #dispatch_searches(partition_file)
    finalize_partition_status(partition_file,lock)

if __name__ == "__main__":
    main()

