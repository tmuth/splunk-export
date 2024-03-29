#!/usr/bin/env python
# coding: utf-8

import re,os,sys,tempfile,multiprocessing,random
from datetime import datetime, timedelta
from pprint import pprint
import dateutil.parser
import json,shutil,itertools,gzip
import logging
#import configparser
import splunklib.client as client
import splunklib.results as results
from time import sleep
from splunk_hec import splunk_hec
import configargparse
import hashlib,secrets,csv
from tendo import singleton
import boto3
from smart_open import open as smart_open
# pip install configparser,dateutil,splunk-sdk,splunk-hec-ftf,configargparse

__author__ = "Tyler Muth"
__source__ = "https://github.com/tmuth/splunk-export"
__license__ = "MIT"
__version__ = "20230228_215453"


# if len(sys.argv) < 2:
#     print("Pass the name of a config file as argument 1")
#     exit(1)

#if not os.path.exists(sys.argv[1]):
#    print("Cannot find the configuration file: "+sys.argv[1])
#    exit(1)
#config_file='export1.conf'
#config_file=sys.argv[1]
logger = logging.getLogger(__name__)
logger_UI = logging.getLogger("UI")
logger_UI.propagate = False
logging.getLogger("splunklib.binding").setLevel(logging.INFO)

def set_logging_level(log_level_in=None):
    if options.log_format=='text':
        logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(name)-12s %(funcName)s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%dT%H:%M:%S')
        logging.getLogger("UI").setLevel(logging.ERROR)
    elif options.log_format=='json':
        
        logging.basicConfig(level=logging.DEBUG,
                    format='{"timestamp": "%(asctime)s.%(msecs)03d", "name": "%(name)s", "module": "%(funcName)s", "level": "%(levelname)s", "message": "%(message)s"}',
                    datefmt='%Y-%m-%dT%H:%M:%S')
        # If the log format is json, setup a separate logger to send events that the Web UI can interpret, like a progress bar
        
        ui_handler = logging.StreamHandler()
        ui_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(fmt='{"timestamp": "%(asctime)s.%(msecs)03d", "name": "%(name)s", "module": "%(funcName)s", "level": "%(levelname)s", "message": %(message)s,"component": "%(component)s"}',
                                      datefmt='%Y-%m-%dT%H:%M:%S')
        ui_handler.setFormatter(formatter)
        # print(ui_logger.handlers)
        logger_UI.addHandler(ui_handler)
        # print(logger_UI.handlers)

        # Handle the case where no value for component was set in the extra attributes of the log message
        class uiLogFilter(logging.Filter):
            def filter(self, record):
                if not hasattr(record, 'component'):
                    record.component = '--'
                # if not re.search(r"^{", str(record.msg)):
                if "{" not in str(record.msg): 
                    # record.msg = record.msg.replace('"', '')
                    # record.msg = '"'+str(record.msg)+'"'
                    record.msg = "".join(['"', str(record.msg),'"'])
                # if not hasattr(record, 'key'):
                #     record.key = ''
                # if not hasattr(record, 'value'):
                #     record.value = ''
                return True
            
        # logger_UI.filters.clear()
        logger_UI.addFilter(uiLogFilter())
        # logging.getLogger("UI").basicConfig(format=uiFormat)
        
    # global logger
    # logger = logging.getLogger()
    # logger.handlers[0].stream = sys.stdout
    if log_level_in is None:
        log_level_config = options.log_level.upper()
    else:
        log_level_config=log_level_in
    #log_level_config = options.log_level.upper()
    #log_level_config=re.sub(r"([A-Z]+).*", r"\1", log_level_config)
    level = logging.getLevelName(log_level_config) #
    logger.setLevel(level)
    #print(logger.getEffectiveLevel())

    # Use in functions to enable custom log level
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    # global logger_progress
    # logger_progress = logging.getLogger("progress") 



def load_config():
    p = configargparse.ArgParser()
    p.add('-c', '--my-config', required=False, is_config_file=True, help='config file path')
    p.add('--SPLUNK_HOST', required=True, help='')
    p.add('--SPLUNK_PORT', required=True, help='')
    p.add('--SPLUNK_AUTH_TOKEN', required=True, help='Pass it in directly or set an environment variable and pass in the name of the environment variable enclosed %. For example %DEV_TOKEN%',env_var='SPLUNK_AUTH_TOKEN')


    p.add('--HEC_HOST', required=False, help='')
    p.add('--HEC_PORT', required=False, help='')
    p.add('--HEC_TOKEN', required=False, help='')
    p.add('--HEC_TLS', required=False, help='')
    p.add('--HEC_TLS_VERIFY', required=False, help='')


    #indexes', required=True, help='')
    p.add('--indexes', required=True, help='')
    #sourcetypes', required=True, help='')
    p.add('--sourcetypes', required=False, help='')
    p.add('--begin_date', required=True, help='')
    p.add('--end_date', required=True, help='')
    p.add('--extra', required=False, help='')

    p.add('--log_level', required=True, help='')
    p.add('--parition_units', required=True, help='')
    p.add('--partition_interval', required=True, help='')
    p.add('--directory', required=False, help='Directory to write data files to',default='../')
    p.add('--parallel_processes', required=False, help='',default=1)
    p.add('--job_location', required=False, help='Path to store the catalog for this job', default='../')
    p.add('--job_name', required=True, help='Name for this job which will be a sub-directory of job_location')
    p.add('--output_destination', required=False, default='file', help='file | hec | s3')
    p.add('--gzip', required=False, help='')
    p.add('--output_format', required=False, help='json | raw | csv',default='json')
    p.add('--resume_mode', required=False, help='', default='false')
    p.add('--incremental_mode', required=False, help='', default='false')
    p.add('--incremental_time_source', required=False, help='file | search', default="file")
    p.add('--max_file_size_mb', default='0', help='')
    p.add('--sample_ratio', default='0', help='The integer value used to calculate the sample ratio. The formula is 1 / <integer>.')
    p.add('--keep_n_jobs', default=10, help='Number of previous partition files to keep')
    p.add('--s3_uri', default='', help='The full path of the bucket to write files to ie s3://export-test-tmuth/test1/test1.txt')
    p.add('--log_format', required=False, help='text | json', default='text')

    global options
    options = p.parse_args()

    token_match=re.search("%.+%",options.SPLUNK_AUTH_TOKEN)
    if token_match:
        # print(options.SPLUNK_AUTH_TOKEN)
        env_var=re.sub(r"%(.+)%","\\1",options.SPLUNK_AUTH_TOKEN)
        # print(env_var)
        env_var_val=os.environ.get(env_var)
        # print(env_var_val)
        options.SPLUNK_AUTH_TOKEN=env_var_val

    options_hash = checksum_var(p.format_values())
    # print(options)
    # print(p.format_help())
    return options_hash

    
def get_globals():
    job_id=datetime.now().strftime('%Y%m%d_%H%M%S%f')[:-3]
    # catalog_dir=os.path.join(options.job_location,'splunk-export-catalog')
    catalog_dir=os.path.join(options.job_location,'.splunk-export-catalog')
    job_name=options.job_name
    # if options.incremental_mode:
    job_partition_name=options.job_name+'-'+job_id
    # else:
        # job_partition_name=options.job_name
    job_path=os.path.join(catalog_dir,job_name)
    job_partition_name=job_partition_name+'.json'
    job_partition_path=os.path.join(job_path,job_partition_name)

    # jobs_file_path=os.path.join(job_path,job_name+'.jobs')
    jobs_file_path=get_jobs_file_path()
    output_directory=os.path.join(options.directory,options.job_name)

    global global_vars
    
    if 'global_vars' not in globals():
        global_vars={
            # 'job_id':secrets.token_hex(nbytes=8),
            'job_id': job_id,
            'catalog_dir':catalog_dir,
            'job_name':job_name,
            'job_path':job_path,
            'jobs_file_path':jobs_file_path,
            'job_partition_name':job_partition_name,
            'job_partition_path':job_partition_path,
            'output_directory': output_directory
            }
        
    return None


def create_output_dir(path_in):
    path_new=os.path.normpath(path_in)
    
    if not os.path.exists(path_new):
        os.makedirs(path_new)

def create_catalog():
    # pprint(global_vars)
    # catalog_dir=os.path.join(options.job_location,'.splunk-export-catalog')
    create_output_dir(global_vars["catalog_dir"])
    create_output_dir(global_vars["job_path"])

def build_search_string(partition_in):
    logger.debug('build_search_string-start')
    logger.debug('indexes: %s',options.indexes)
    logger.debug('extra: %s',options.extra)
    s='search index='+partition_in["index"]
    if options.sourcetypes:
        s+=' sourcetype='+partition_in["sourcetype"]
    s+=' '+str(options.extra)
    
    logger.debug('s: %s',s)
    logger.debug('build_search_string-end')
    return s

def explode_date_range(begin_date_in: str,end_date_in: str,interval_unit_in: str,interval_in: int):
    logger.debug('explode_date_range-start')
    logger.debug('begin_date_in: %s',begin_date_in)
    logger.debug('end_date_in: %s',end_date_in)
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
        logger.debug('end_current: %s',end_current)
        result.append ([begin_current,end_current])
        #begin_current=end_current+timedelta(seconds=1)
       
        
        begin_current=end_current
        logger.debug('begin_current: %s',begin_current)
    logger.debug('explode_date_range-end')
    return result

def search_splunk_for_sourtypes(index_list_in,date_array_in):
    logger.debug('search_splunk_for_sourtypes-start')
    result_list=[]
    for index in index_list_in:
        service=connect()
        logger.debug('Index: %s',index)
        logger.debug('date_earliest: %s',min(date_array_in))
        logger.debug('date_earliest: %s',max(date_array_in))
        
        search_string=' | metasearch index='+index+' sourcetype=* | stats count by index, sourcetype | fields - count'
        logger.debug('search: %s',search_string)
        earliest_date=min(date_array_in[0])
        latest_date=max(date_array_in[1])
        job=search(service,search_string,earliest_date.isoformat(),latest_date.isoformat())
        reader = results.JSONResultsReader(job)
        
        for result in reader:
            logger.debug(result)
            result_list.append((result['index'],result['sourcetype']))

        #pprint(result_list)
    return result_list
    

def get_index_sourcetype_array(date_array_in):
    index_count=0
    sourcetype_count=0
    if not options.sourcetypes:
        out_array=options.indexes.split(",")
        index_count=len(out_array)
    else:
        #logger = logging.getLogger()
        #logger.setLevel(logging.DEBUG)
        if options.sourcetypes == '*':
            index_list=options.indexes.split(",")
            index_count=len(index_list)
            #logging.info('Index Count: %s',len(index_list))
            out_array=search_splunk_for_sourtypes(index_list,date_array_in)
            #sys.exit("Exit early")
        else:
            index_list=options.indexes.split(",")
            logging.info('Index list: %s',index_list)
            sourcetype_list=options.sourcetypes.split(",")
            out_array = itertools.product(index_list, sourcetype_list)
            logging.info('out_array: %s',out_array)
            index_count=len(index_list)
            sourcetype_count=len(sourcetype_list)

    return out_array,index_count,sourcetype_count

def write_resume_summary(partition_file_in):
    with open(partition_file_in,'r+') as f:
        data = json.load(f)
        data["summary_data"]["start_time"]=datetime.now().isoformat()
        data["summary_data"]["status"] = 'resume'

        i=1
        for search_partition in data["partitions"]:
            if search_partition["status"]!='complete':
                search_partition["status"]='not started'
                search_partition["pid"]=''
                i+=1

        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()
        return i


def checksum_file(filename, hash_factory=hashlib.md5, chunk_num_blocks=128):
    h = hash_factory()
    with open(filename,'rb') as f: 
        for chunk in iter(lambda: f.read(chunk_num_blocks*h.block_size), b''): 
            h.update(chunk)
    return h.hexdigest()

def checksum_var(text_in):
    var = text_in.encode('utf-8')
    hashed_var = hashlib.md5(var).hexdigest()
    return hashed_var

def get_catalog_path():
    catalog_dir=os.path.join(options.job_location,'.splunk-export-catalog')
    # catalog_dir=os.path.join(options.job_location,'splunk-export-catalog')
    # job_name=options.job_name
    job_name=options.job_name
    job_path=os.path.join(catalog_dir,job_name)
    return job_path

def get_jobs_file_path():
    job_name=options.job_name
    job_path=get_catalog_path()
    jobs_file_path=os.path.join(job_path,job_name+'.jobs')
    logger.info('jobs_file_path: %s',os.path.abspath(jobs_file_path))
    return jobs_file_path

def check_previous_run_succeeded():
    jobs_file_path=get_jobs_file_path()
    logger.debug("jobs_file_path: %s",jobs_file_path)
    if not os.path.isfile(jobs_file_path):
        logger.debug("The job file doesn't exist so it's the first run of a job")
        return True
    
    with open(jobs_file_path,'r') as f:
        json_data = json.load(f)
    # json_data = json.load(data)
    last_job=json_data[-1]

    # print(last_job["status"])

    if last_job["status"] != "complete":
        logger.debug("The last run did not complete")
        return False
    else:
        logger.debug("The last run did complete")
        return True

def cleanup_failed_run(partition_file_in):
    logging.info('cleanup_failed_run-start')
    # logging.info(partition_file_in)


    def backup_partition_file(previous_part_file_in,fail_job_id_in):
        failed_job_partition_name=options.job_name+'-'+fail_job_id_in+'.json'
        failed_job_partition_path=os.path.join(global_vars["job_path"],failed_job_partition_name)
        previous_part_path=os.path.join(global_vars["job_path"],previous_part_file_in)
        shutil.copy(previous_part_path, failed_job_partition_path)
        return failed_job_partition_name

    if options.resume_mode!='resume':
        return False,0

    # if not os.path.isfile(partition_file_in):
    #     logger.debug("Partition file does not exist: %s",partition_file_in)
    #     return False,0
    # else:
    # cleanup jobs file
    jobs_file_path=get_jobs_file_path()
    logger.debug("jobs_file_path: %s",jobs_file_path)
    if not os.path.isfile(jobs_file_path):
        return False,0
    else:
        with open(jobs_file_path,'r') as f:
            json_data = json.load(f)

        last_job=json_data[-1]
        if last_job["status"] != "complete":
            logger.debug("The last run did not complete")
            partition_file=os.path.join(get_catalog_path(),last_job["partition_file"])

            failed_job = json_data[-1].copy()

            last_job_id=json_data[-1]["job_id"]
            i=0
            while True:
                print(i)
                new_last_job_id=last_job_id+'.'+str(i)
                if not any(d['job_id'] == new_last_job_id for d in json_data):
                    # last_job_id=x
                    json_data[-1]['job_id']=new_last_job_id
                    break
                if i > 20:
                    break
                i+=1

            json_data[-1]['status']='failed'
            
            failed_job['status']='resume'
            
            previous_partition_name=json_data[-1]['partition_file']

            backup_partition_file=backup_partition_file(previous_partition_name,new_last_job_id)
            json_data[-1]['partition_file']=backup_partition_file
            json_data.append(failed_job)

            failed_job_data={
                'job_id':failed_job['job_id'],
                'partition_file':partition_file
            }
            json_doc=format_jobs_json(json_data)
            with open(jobs_file_path, "w") as outfile:
            # print('\n'.join(json_doc),file=outfile)
                print(json_doc,file=outfile)


            return False,failed_job_data
        else:
            logger.debug("The last run did complete")
            return True,None



def format_jobs_json(json_in):
    json_doc=json.dumps(json_in, indent=None, sort_keys=False,separators =(",", ":"))   
    json_doc=re.sub(r"^\[", r"[\n", json_doc)
    json_doc=re.sub(r"\]$", r"\n]", json_doc)
    json_doc=re.sub(r"},{", r"},\n{", json_doc)
    return json_doc

def cleanup_old_jobs(job_list_in):
    logger.debug('Deleting %s old jobs',len(job_list_in))
    for job in job_list_in:
        # print(job["job_id"])
        partition_file=os.path.join(global_vars["job_path"],job["partition_file"])
        logger.debug('Partition file: %s',partition_file)
        if os.path.exists(partition_file):
            logger.debug(partition_file)
            os.remove(partition_file)

def resume_job_file():
    None

def finalize_job_file(summary_in):
    with open(global_vars["jobs_file_path"],'r+') as f:
            json_data = json.load(f)
    # keep_n_jobs

    delete_first_n_jobs=len(json_data)-options.keep_n_jobs
    logger.debug('Delete %s jobs',delete_first_n_jobs )
    delete_jobs=json_data[:delete_first_n_jobs]
    cleanup_old_jobs(delete_jobs)

    keep_jobs=json_data[-options.keep_n_jobs:].copy()
    logger.debug('Keep %s jobs',len(keep_jobs) )

    keep_jobs[-1]["status"]='complete'
    keep_jobs[-1]["end_time"]=summary_in["end_time"]
    # for job in keep_jobs:
    #         if job["job_id"]==global_vars["job_id"]:
    #             logger.debug('Job id %s',job["job_id"] )
    #             job["status"]='complete'
    #             job["end_time"]=summary_in["end_time"]
    #             break

    json_doc = format_jobs_json(keep_jobs)
    
    # jobs_file=os.path.abspath(global_vars["jobs_file_path"])
    # partition_file=os.path.abspath(global_vars["partition_file_path"])
    logger.debug('Jobs File %s',os.path.abspath(global_vars["jobs_file_path"]) )
    logger.debug('Partition File %s',os.path.abspath(global_vars["job_partition_path"]) )

    with open(global_vars["jobs_file_path"], "w") as outfile:
        # print('\n'.join(json_doc),file=outfile)
        print(json_doc,file=outfile)

def write_job_file(summary_data_in):
    #job_data=[]
    json_data = []
    if os.path.exists(global_vars["jobs_file_path"]):
        with open(global_vars["jobs_file_path"],'r+') as f:
            json_data = json.load(f)
            # pprint(dir(json_data))

        # json_data['jobs'] = ''
    
    job_summary = {
        'job_id'        : summary_data_in["job_id"],
        'options_hash'  : summary_data_in["options_hash"],
        'start_time'    : summary_data_in["start_time"],
        'end_time'    : summary_data_in["end_time"],
        'status'    : summary_data_in["status"],
        'partition_file':global_vars["job_partition_name"]
    }
    json_data.append(job_summary)
    #pprint(json_data)
    json_doc = format_jobs_json(json_data)
    

    with open(global_vars["jobs_file_path"], "w") as outfile:
        # print('\n'.join(json_doc),file=outfile)
        print(json_doc,file=outfile)
        # outfile.write(result)

def get_previous_run_latest_dates(new_partitions_in):
    json_data = []
    if os.path.exists(global_vars["jobs_file_path"]):
        logger.debug('jobs_file_path: %s',global_vars["jobs_file_path"])
        with open(global_vars["jobs_file_path"],'r+') as f:
            json_data = json.load(f)
        previous_job = json_data[-1].copy()
        previous_partition_file=os.path.join(global_vars["job_path"],previous_job["partition_file"])
        previous_partitions=[]
        with open(previous_partition_file,'r+') as f:
            previous_partitions = json.load(f)

        updated_partitions=new_partitions_in

        for u in updated_partitions:
            #pprint(u)
            for p in previous_partitions["partitions"]:
                # pprint(p)
                if u["index"]==p["index"] and u["sourcetype"]==p["sourcetype"] and \
                    p["latest_returned"]:
                    u["earliest"]=p["latest_returned"]
                    u["latest"]=datetime.now().isoformat()

        return updated_partitions



def write_search_partitions(date_array_in,options_hash_in,previous_run_succeeded_in):
    logger.debug('write_search_partitions-start')
    index_sourcetype_array,index_count,source_type_count=get_index_sourcetype_array(date_array_in)
    json_data = {}
    result_list = []
    i=0
    for index_st_entry in index_sourcetype_array:
        for entry in date_array_in:
            i+=1
            
            search_partition={'id':i,
                'earliest': entry[0].isoformat(),'latest':entry[1].isoformat(),
                             'status':'not started','result_count':'','pid':''}
            if options.incremental_mode.lower() =='true' and options.incremental_time_source.lower()=='file':
                search_partition['latest_returned']=''

            sourcetype_str=''
            if type(index_st_entry) == tuple: 
                search_partition['index']=index_st_entry[0]
                search_partition['sourcetype']=index_st_entry[1]
            else:
                search_partition['index']=index_st_entry

            result_list.append(search_partition)
    

    # update with incremental earliest
    if options.incremental_mode.lower() =='true' and options.incremental_time_source.lower()=='file'\
         and previous_run_succeeded_in:
        updated_partitions=get_previous_run_latest_dates(result_list)
        # pprint(updated_partitions)
        result_list=updated_partitions

    logging.info("Total Partitions: %s",i)
    global_vars["partition_count"]=i

    summary_data={'partition_count': i,
                  'complete_count': 0,
                  'status': 'starting',
                  'start_time': datetime.now().isoformat(),
                  'end_time': '',
                  'indexes':index_count,
                  'sourcetypes':source_type_count,
                  'options_hash':options_hash_in,
                  'job_id':global_vars["job_id"],
                  'controller_pid':os.getpid(),
                  'total_seconds': '',
                  'total_results': '0'}

    if source_type_count>0:
        summary_data['sourcetypes']=source_type_count
    
    json_data['summary_data']=summary_data
    json_data['partitions']=result_list
    
    search_partitions=json.dumps(json_data, indent=2, sort_keys=False)
    #print(search_partitions)      
    
    write_job_file(summary_data)

    with open(global_vars["job_partition_path"], "w") as outfile:
        outfile.write(search_partitions)
    
    d={'component':'job_info'}
    v=os.path.abspath(global_vars["jobs_file_path"])
    logger_UI.info('{"key": "Jobs File","value":"%s"}',v,extra=d)
    v=os.path.abspath(global_vars["job_partition_path"])
    logger_UI.info('{"key": "Partition File","value":"%s"}',v,extra=d)
    
    logger.info('Jobs File %s',os.path.abspath(global_vars["jobs_file_path"]) )
    logger.info('Partition File %s',os.path.abspath(global_vars["job_partition_path"]) )
    logger.debug('write_search_partitions-end')
    return int(summary_data["partition_count"])

def update_partition_status(partition_file_in,partition_in,status_in,lock_in,result_count_in,last_date_in):
    logger.debug('update_partition_status-start')
    logger.debug('result_count_in: %s',result_count_in)
    logger.debug('last_date_in: %s',last_date_in)
    lock_in.acquire()
    with open(partition_file_in,'r+') as f:
        data = json.load(f)
        search_partition_out=None
        for search_partition in data["partitions"]:
            if search_partition["id"]==partition_in["id"]:
                #pprint(search_partition["earliest"])
                search_partition["status"]=status_in
                search_partition["result_count"]=result_count_in
                if options.incremental_mode.lower()=='true' and options.incremental_time_source.lower()=='file' and last_date_in is not None:
                    search_partition["latest_returned"]=last_date_in.isoformat()
                
                #return search_partition
                break
                
        if status_in == 'complete':
            data["summary_data"]["complete_count"]=int(data["summary_data"]["complete_count"])+1
            pct_complete=round((data["summary_data"]["complete_count"]/global_vars["partition_count"])*100)
            d={'component':'progress'}
            logger_UI.info(pct_complete,extra=d)
            # logger_UI.info(pct_complete)
            logger.info("Completed Partition %s of %s - %%%s Complete",data["summary_data"]["complete_count"],global_vars["partition_count"],pct_complete)
            data["summary_data"]["total_results"]=int(data["summary_data"]["total_results"])+int(result_count_in)
            
            
        json_object = json.dumps(data, indent=4)
        f.seek(0)
        f.write(json_object)
        f.truncate()
    lock_in.release()
    logger.debug('update_partition_status-end')

def finalize_partition_status(partition_file_in,lock_in):
    lock_in.acquire()
    summary_data=[]
    with open(partition_file_in,'r+') as f:
        #portalocker.lock(f, portalocker.LOCK_EX)
        data = json.load(f)
        summary_data=data["summary_data"]
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
    finalize_job_file(summary_data)
        
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
    logger.debug('search_export-start')

    logger.debug(service_in)
    logger.debug(search_in)
    logger.debug(partition_in["earliest"])
    logger.debug(partition_in["latest"])
    #pprint(search_in)
    #search_id="splunk_export_search_"+str(round(random.uniform(10000000, 90000000),4))
    search_id=str(round(random.uniform(10000000, 90000000),4))
    logger.debug("Search ID: %s, OS Process ID: %s",search_id,os.getpid())
    kwargs_export = {"search_mode": "normal",
                     'earliest_time': partition_in["earliest"],
                     'latest_time': partition_in["latest"],
                     "output_mode": "json",
                     "count":0,
                     "preview":"false",
                     "id":search_id}

    if int(options.sample_ratio) > 0:
        kwargs_export["sample_ratio"]=options.sample_ratio
    # Changing the log level to DEBUG globally changes it for the Splunk SDK search too which can be too noisy. Overriding here. 
    # set_logging_level('WARN')

    job = service_in.jobs.export(search_in, **kwargs_export)
    # set_logging_level()
    logger.debug("search_export-end")

    return job

def search(service_in,search_in,earliest_in,latest_in):
    logger.debug('search-start')

    logger.debug(service_in)
    logger.debug(search_in)
    
    kwargs_export = {"search_mode": "normal",
                     'earliest_time': earliest_in,
                     'latest_time': latest_in,
                     "output_mode": "json",
                     "count":0,
                     "preview":"false"}
    job = service_in.jobs.export(search_in, **kwargs_export)
    
    
    logger.debug("search-end")

    return job

def dispatch_searches(partition_file_in,options_in,lock_in,global_vars_in):
    
    logger.info('dispatch_searches-start')
    global options
    options=options_in
    global global_vars

    
    global_vars=global_vars_in
    set_logging_level()

    while True:
    #while False:
        partition_out=get_search_partition(partition_file_in,lock_in)

        if partition_out is not None:
            search_string=build_search_string(partition_out)
            service=connect()
            job=search_export(service,search_string,partition_out)
            # set_logging_level()
            #print_results(job)
            results=write_results(job,partition_out)
            update_partition_status(partition_file_in,partition_out,'complete',lock_in,results["count"],results["last_time_stamp"])
            #job.cancel()
        else:
            break

    logger.debug('dispatch_searches-end')

def split_s3_path(s3_path):
    path_parts=s3_path.replace("s3://","").split("/")
    bucket=path_parts.pop(0)
    key="/".join(path_parts)
    return bucket, key

def write_results(job_in,partition_in):
    if options.output_destination=='file' or options.output_destination=='s3':
        return write_results_to_file(job_in,partition_in)

    if options.output_destination=='hec':
        return send_results_to_hec(job_in,partition_in)

def send_results_to_hec(job_in,partition_in):
    
    hec_server=options.HEC_HOST
    hec_port=options.HEC_PORT
    hec_token=options.HEC_TOKEN
    use_hec_tls=options.HEC_TLS
    hec_tls_verify=options.HEC_TLS_VERIFY

    # https://gitlab.com/johnfromthefuture/splunk-hec-library
    # Create an object reference to the library, initalized with our settings.
    input_type='raw'
    splhec = splunk_hec( token=hec_token, hec_server=hec_server, hec_port=hec_port,
                        use_hec_tls=use_hec_tls,hec_tls_verify=hec_tls_verify,
                        logger=logging,input_type=input_type )

    
    last_time_stamp=None
    payload = {}
    try:
        reader = results.JSONResultsReader(job_in)
        i=0
        for result in reader:
            
            i+=1
            #pprint(result)
            if isinstance(result, dict):
                # Note dateutil.parser.parse() took double the time for 90k events
                time_stamp=datetime.strptime(result["_time"],'%Y-%m-%d %H:%M:%S.%f %Z').strftime('%s')
                if options.incremental_mode and options.incremental_time_source=='file':
                    last_time_stamp=datetime.strptime(result["_time"],'%Y-%m-%d %H:%M:%S.%f %Z')
                

                splhec.set_request_params({'_time':time_stamp,'index':result["index"], 'sourcetype':result["sourcetype"], 'source':result["source"]})
                #logger.debug("result-sourcetype: %s",result["index"])
                #pprint(result)
                payload=str(result["_raw"])
                #payload['event']=str(result["_raw"])
                #payload['time'] = result["_time"]
                #payload['index'] = result["index"]
                #payload['source'] = result["source"]
                #payload['sourcetype'] = result["sourcetype"]
                splhec.send_event(payload)
            elif isinstance(result, results.Message):
                # Diagnostic messages may be returned in the results
                logging.info('result: %s',result)
    except Exception as Argument:
        logging.exception('Send to HEC error')
    finally:
        logger.debug("Result count: %s",i)
        splhec.stop_threads_and_processing()
        result_summary={'count':i,'last_time_stamp':last_time_stamp}
        return result_summary


def write_results_to_file(job_in,partition_in):
    logger.debug('write_results-start')
    
    earliest=partition_in["earliest"]
    earliest=re.sub("[/:]", "-", earliest)
    

    if options.output_destination.lower()=='file':
        file_path=os.path.join(global_vars["output_directory"],partition_in["index"])
        create_output_dir(file_path)

        if "sourcetype" in partition_in:
            # file_path=options.directory+'/'+partition_in["index"]+'/'+partition_in["sourcetype"]
            file_path=os.path.join(global_vars["output_directory"],partition_in["index"],partition_in["sourcetype"])
            create_output_dir(file_path)
            file_name=os.path.join(file_path,partition_in["index"]+"_"+partition_in["sourcetype"]+"_"+earliest)
        else:
            file_name=os.path.join(file_path,partition_in["index"]+"_"+earliest)
    else:
        if "sourcetype" in partition_in:
            # file_path=options.directory+'/'+partition_in["index"]+'/'+partition_in["sourcetype"]
            file_path=options.s3_uri+'/'+options.job_name+'/'+partition_in["index"]+'/'+partition_in["sourcetype"]
            file_name=file_path+'/'+partition_in["index"]+"_"+partition_in["sourcetype"]+"_"+earliest
        else:
            file_path=options.s3_uri+'/'+options.job_name+'/'+partition_in["index"]
            file_name=file_path+'/'+partition_in["index"]+"_"+earliest

    empty_result=True
    file_number=0
    def get_new_file_name(file_name_in):
        version_extension=''
        output_extension=''
        output_format=options.output_format.lower()
        if output_format=='json':
            output_extension='.json'
        elif output_format=='raw':
            output_extension='.txt'
        elif output_format=='csv':
            output_extension='.csv'

        if options.gzip=='true':
            output_extension=output_extension+'.gz'

        if file_number > 0:
            version_extension='.'+str(file_number)

        if options.output_destination=='file':
            output_file_temp_local=file_name_in+version_extension+".tmp"
            output_file_temp_local=os.path.normpath(output_file_temp_local)
            output_file_local=file_name_in+version_extension+output_extension
            output_file_local=os.path.normpath(output_file_local)
        else:
            #s3
            tmp_extension='.tmp'
            if options.gzip=='true':
                tmp_extension='.tmp.gz'
            output_file_temp_local=file_name_in+version_extension+tmp_extension
            output_file_local=file_name_in+version_extension+output_extension


        return output_file_temp_local,output_file_local

    output_file_temp,output_file=get_new_file_name(file_name)
    logger.debug('output_file_temp: %s',output_file_temp)

    def open_file(output_file_temp_in):
        if options.gzip=='true' and options.output_destination=='file':
            f_out = gzip.open(output_file_temp_in, compresslevel=9, mode='wt')
            # output_file=output_file+'.gz'
        elif options.output_destination=='s3':
            # set_logging_level('WARN')
            f_out = smart_open(output_file_temp_in, 'w')
        else:
            f_out = open(output_file_temp_in, "w")
        return f_out

    def check_file_size(file_handle_in,check_size_loops_in):
        # this function is used to change the number of loops at which we check the file size to balance accuracy with speed
        # need to refactor to be more mathy and lest hacky
        current_size_mb = file_handle_in.tell()/1024/1024
        current_size_percent=(current_size_mb/int(options.max_file_size_mb))*100
        divide_by=2
        check_size_loops_return=check_size_loops_in
        if current_size_percent>=95:
            divide_by=int(abs(91-current_size_percent))+2
            check_size_loops_return=int(check_size_loops_in/divide_by)
        if check_size_loops_return<10:
            check_size_loops_return=10
        if current_size_percent>=98:
            check_size_loops_return=5
        if current_size_percent>=99.5:
            check_size_loops_return=1

        return check_size_loops_return,current_size_mb


    check_size_loops=10000000000
    if int(options.max_file_size_mb)>0:
        check_size_loops=100*int(options.max_file_size_mb)
        check_size_loops_orig=check_size_loops
    
    f = open_file(output_file_temp)
    output_format=options.output_format.lower()
    if output_format=='csv':
        csv_writer = csv.writer(f)

    last_time_stamp=None
    
    # need to refactor this scection to be more modular and readable
    try:
        reader = results.JSONResultsReader(job_in)
        i=0
        counter_per_file=0
        for result in reader:
            
            i+=1
            if isinstance(result, dict):
                empty_result=False
                #logger.debug("Non-Empty result")
                #logger.debug(result["_time"])

                if options.incremental_mode.lower() =='true' and options.incremental_time_source.lower()=='file':
                    if last_time_stamp is None:
                        last_time_stamp=datetime.strptime(result["_time"],'%Y-%m-%d %H:%M:%S.%f %Z')
                    else:
                        current_time_stamp=datetime.strptime(result["_time"],'%Y-%m-%d %H:%M:%S.%f %Z')
                        last_time_stamp=max(current_time_stamp,last_time_stamp)
                    # logger.debug("last time: %s",last_time_stamp )
                

                
                if output_format=='json':
                    print(result,file=f)
                elif output_format=='raw':
                    print(result["_raw"],file=f)
                elif output_format=='csv':
                    if counter_per_file == 0:
                    # Write CSV Headers
                        header = result.keys()
                        csv_writer.writerow(header)

                    # Write CSV data
                    csv_writer.writerow(result.values())


                counter_per_file+=1
                if (int(options.max_file_size_mb)>0 and i % check_size_loops == 0) :
                    check_size_loops,current_size=check_file_size(f,check_size_loops)
                    if current_size >= float(options.max_file_size_mb):
                        logger.debug("Reached file size limit %s: ",current_size)
                        check_size_loops=check_size_loops_orig
                        f.close()
                        
                        if file_number == 0:
                            file_number+=1
                            dummy,output_file=get_new_file_name(file_name)
                        
                        logger.debug("Result count for:%s is %s",output_file,i)
                        if options.output_destination.lower()=='file':
                            os.rename(output_file_temp,output_file)
                        else:
                            bucket, tmp_key = split_s3_path(output_file_temp)
                            bucket, final_key = split_s3_path(output_file)
                            logger.debug("bucket: %s,tmp_key: %s, final_key: %s",bucket,tmp_key,final_key)
                            s3 = boto3.resource('s3')
                            copy_source = {
                                'Bucket': bucket,
                                'Key': tmp_key
                            }
                            s3.meta.client.copy(copy_source, bucket, final_key)
                            s3.Object(bucket, tmp_key).delete()
                        file_number+=1
                        output_file_temp,output_file=get_new_file_name(file_name)
                        logger.debug("output_file_temp,output_file: %s,%s ",output_file_temp,output_file)
                        f = open_file(output_file_temp)
                        counter_per_file=0
                        
        
            elif isinstance(result, results.Message):
                # Diagnostic messages may be returned in the results
                #print(vars(job_in))
                logger.debug("Empty result")
                logger.debug("Diagnostic message: %s",result)
                i=0
        #last_time_stamp=datetime.strptime(max(result["_time"]),'%Y-%m-%d %H:%M:%S.%f %Z')
        #logger.debug("last time max: %s",last_time_stamp )
    except Exception as Argument:
        logging.exception('Write to file error')
    finally:
        # set_logging_level(options.log_level)
        logger.debug("Result count: %s",i)

        if options.output_destination.lower()=='file':
            if empty_result:
                f.close()
                os.remove(output_file_temp)
            else:
                if f.tell() == 0:
                    f.close()
                    os.remove(output_file_temp)
                else:
                    os.rename(output_file_temp,output_file)
                    f.close()
        else:
            s3 = boto3.resource('s3')
            bucket, tmp_key = split_s3_path(output_file_temp)
            bucket, final_key = split_s3_path(output_file)
            logger.debug("bucket: %s,tmp_key: %s, final_key: %s",bucket,tmp_key,final_key)
            if empty_result:
                f.close()
                s3.Object(bucket, tmp_key).delete()
            else:
                if f.tell() == 0:
                    f.close()
                    s3.Object(bucket, tmp_key).delete()
                else:
                    f.close()
                    copy_source = {
                        'Bucket': bucket,
                        'Key': tmp_key
                    }
                    s3.meta.client.copy(copy_source, bucket, final_key)
                    s3.Object(bucket, tmp_key).delete()
                    



        
        logger.debug('write_results-end')
        result_summary={'count':i,'last_time_stamp':last_time_stamp}
        return result_summary

        
def connect():
    try:
        logger.debug('connect-start')
        logger.debug('SPLUNK_HOST: %s',options.SPLUNK_HOST)
        logger.debug('SPLUNK_PORT: %s',options.SPLUNK_PORT)
        logger.debug('SPLUNK_AUTH_TOKEN: %s',options.SPLUNK_AUTH_TOKEN)
       
        service = client.connect(
            host=options.SPLUNK_HOST,
            port=options.SPLUNK_PORT,
            splunkToken=options.SPLUNK_AUTH_TOKEN,
            autologin=True)
        logger.debug(service)
        logger.debug('connect-successful')
        logger.debug('connect-end')
        return service
    except:
        logging.error('connect-failed')
def get_server_info():
    service=connect()
    # getattr(service, 'info')
    info=service.info
    log_keys=['serverName','numberOfVirtualCores','os_name_extended','product_type','physicalMemoryMB','version']
    for k,v in info.items():
        if k in log_keys:
            d={'component':'server_info'}
            logger.info("Key: %s, Value: %s",k,v)
            # d={'component':'server_info','key':k,'value':v}
            logger_UI.info('{"key": "%s","value":"%s"}',k,v,extra=d)
            # print("Key: %s, Value: %s",k,v)

def main():
    
    options_hash = load_config()
    try:
        current_instance = singleton.SingleInstance()
    except singleton.SingleInstanceException:
        raise SystemExit('Error: multiple instances of splunk-export with the same options cannot run simultaneously.')

    
    get_globals()
    #pprint(global_vars)
    
    set_logging_level()
    
    get_server_info()
    
    # logger_UI.removeFilter
    logger.info('catalog_dir: %s',os.path.abspath(global_vars['catalog_dir']))
    logger.info('output_dir: %s',os.path.abspath(global_vars['output_directory']))
    
    # quit()
    create_catalog()
    previous_run_succeeded=check_previous_run_succeeded()
    # print(previous_run_succeeded)

    
    should_resume=False
    if previous_run_succeeded:
        partition_file=global_vars["job_partition_path"]
    else:
        
        # partition_file=previous_job_data['partition_file']
        # global_vars["job_id"]=previous_job_data['job_id']
        partition_file=global_vars["job_partition_path"]
        should_resume,part_count=cleanup_failed_run(partition_file)
    

    
    # quit()
    if not should_resume:
        if options.incremental_mode.lower() =='true' and options.incremental_time_source.lower()=='file':
            # incremental jobs can only have one date partition per index/sourcetype
            date_array=explode_date_range(options.begin_date,options.end_date,
                                'days',999)
        else:
            date_array=explode_date_range(options.begin_date,options.end_date,
                                    options.parition_units,int(options.partition_interval))
        part_count=write_search_partitions(date_array,options_hash,previous_run_succeeded)
        create_output_dir(global_vars["output_directory"])
    
    # quit()
    # procs = int(options.parallel_processes)   # Number of processes to create
    procs = min(int(options.parallel_processes),part_count)   # Number of processes to create
    logging.info('Number of processes: %s',procs)
    
    lock = multiprocessing.Lock()
    jobs = []


    # from tqdm.auto import tqdm
    # from p_tqdm import p_map, p_umap, p_imap, p_uimap

    # numbers = list(range(0, 8))

    for i in range(0, procs):
        process = multiprocessing.Process(target=dispatch_searches,args=((partition_file,options,lock,global_vars)))
        jobs.append(process)

    # jobs = p_map(dispatch_searches,args=((partition_file,options,lock,global_vars)))

    for j in jobs:
        j.start()

	# Ensure all of the processes have finished
    for j in jobs:
        j.join()
    #dispatch_searches(partition_file)
    finalize_partition_status(partition_file,lock)

#global_vars={}
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Pass the name of a config file as argument 1")
        exit(1)
    main()

