#!/usr/bin/env python
# coding: utf-8

import re,os,sys,tempfile,random
from datetime import datetime, timedelta
from pprint import pprint
import dateutil.parser
import json,shutil,itertools,gzip
import logging
#from splunk-export-parallel import search_export
#import configparser
import splunklib.client as client
import splunklib.results as results
from time import sleep
#from splunk_hec import splunk_hec
import configargparse
# pip install configparser,dateutil,splunk-sdk,splunk-hec-ftf,configargparse

__author__ = "Tyler Muth"
__source__ = "https://github.com/tmuth/splunk-export"
__license__ = "MIT"
__version__ = "20221018_180543"


def load_config():
    p = configargparse.ArgParser()
    p.add('-c', '--my-config', required=False, is_config_file=True, help='config file path')
    p.add('--log_level', required=False, default='INFO', help='DEBUG,INFO,WARNING,ERROR,CRITICAL')
    p.add('--SPLUNK_HOST', required=False, default='localhost', help='')
    p.add('--SPLUNK_PORT', required=False, default='8089', help='')
    p.add('--SPLUNK_AUTH_TOKEN', required=False, help='',env_var='SPLUNK_LAPTOP_TOKEN')
    p.add('--begin_date', required=False, help='',default='2022-10-11')
    p.add('--end_date', required=False, help='',default='2022-10-12')
    p.add('--search', required=False, help='',default='search index=_internal sourcetype=splunkd | head 150000 | streamstats count as row_num| table _time ')
    p.add('--file', required=True, help='')


    global options
    options = p.parse_args()


def set_logging_level(log_level_in=None):
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(funcName)s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

    logger = logging.getLogger()
    logger.handlers[0].stream = sys.stdout
    if log_level_in is None:
        log_level_config = options.log_level.upper()
    else:
        log_level_config=log_level_in
    level = logging.getLevelName(log_level_config) 
    logger.setLevel(level)

def connect():
    try:
        logging.info('connect-start')
        logging.debug('SPLUNK_HOST: %s',options.SPLUNK_HOST)
        logging.debug('SPLUNK_PORT: %s',options.SPLUNK_PORT)
        logging.debug('SPLUNK_AUTH_TOKEN: %s',options.SPLUNK_AUTH_TOKEN)
       
        service = client.connect(
            host=options.SPLUNK_HOST,
            port=options.SPLUNK_PORT,
            splunkToken=options.SPLUNK_AUTH_TOKEN,
            autologin=True)
        logging.debug(service)
        logging.info('connect-successful')
        logging.info('connect-end')
        return service
    except Exception as Argument:
        logging.exception('Splunk Search Error')

def  format_date(date_in):

    if not date_in:
        return_date=datetime.now()
    else:
        return_date = dateutil.parser.parse(date_in)
        
    logging.debug("return_date: %s",return_date)
    #return_date=return_date.strftime('%s')
    return_date=return_date.timestamp()
    logging.debug("return_date: %s",return_date)

    return return_date

def search_export(service_in,search_in,earliest_in,latest_in):
    logging.info('search_export-start')

    logging.debug(service_in)
    logging.debug(search_in)
    search_id=str(round(random.uniform(10000000, 90000000),4))
    logging.debug("Search ID: %s, OS Process ID: %s",search_id,os.getpid())
    kwargs_export = {"search_mode": "normal",
                    'earliest_time': earliest_in,
                    'latest_time': latest_in,
                    "output_mode": "json",
                    "count":0,
                    "preview":"false",
                    "id":search_id}

    job = service_in.jobs.export(search_in, **kwargs_export)
    
    logging.info("search_export-end")

    return job

def write_to_file(job_in):
    
    empty_result=True
    try:
        f = open(options.file, "w")
        reader = results.JSONResultsReader(job_in)
        i=0
        for result in reader:
            if isinstance(result, dict):
                i+=1
                empty_result=False
                print(result,file=f)
                print(result["row_num"])
                if not result["_bkt"]:
                    pprint(result["row_num"])
            elif isinstance(result, results.Message):
                # Diagnostic messages may be returned in the results
                logging.info("Empty result")
                logging.info("Diagnostic message: %s",result)
    except Exception as Argument:
        logging.exception('Write to file error')
    finally:
        logging.debug("Result count: %s",i)
        if empty_result:
            f.close()
            os.remove(options.file)
        else:
            f.close()
        return(i)

def write_to_file2(job_in):

    f = gzip.open(options.file, compresslevel=9, mode='wt')
    #f = open(options.file, "w")
    reader = results.JSONResultsReader(job_in)
    for result in reader:
        # print(result["_raw"])
        print(result["_raw"],file=f)
    # ds = list(reader)
    # #print(ds)
    # pprint(dir(job_in))
    # pprint(dir(reader))
    # print(len(ds))



    
    # for result in reader:
    #     if isinstance(result, dict):
    #         #print("Result: %s" ,result)
    #         # print(result["row_num"])
    #         None
    #     elif isinstance(result, results.Message):
    #         # Diagnostic messages may be returned in the results
    #         print("Message: %s",result)

def main():
    load_config()
    set_logging_level()
    print(options.SPLUNK_HOST)
    try:
        service=connect()
        job=search_export(
            service,
            options.search,
            format_date(options.begin_date),
            format_date(options.end_date)
        )
        #write_to_file(job)
        write_to_file2(job)
    except Exception as Argument:
        logging.exception('Splunk Search Error')
    finally:
        # logging.debug("Result count: %s",i)
        service.logout()

    

if __name__ == "__main__":
    main()