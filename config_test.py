import configargparse,time,re,os

def load_config():
    p = configargparse.ArgParser()
    
    # p.add('-c', '--my-config', required=True, is_config_file=True, help='config file path')
    # p.add('--SPLUNK_HOST', required=True, help='')
    # p.add('--SPLUNK_PORT', required=True, help='')
    # p.add('--SPLUNK_AUTH_TOKEN', required=True, help='',env_var='SPLUNK_LAPTOP_TOKEN')


    # p.add('--HEC_HOST', required=True, help='')
    # p.add('--HEC_PORT', required=True, help='')
    # p.add('--HEC_TOKEN', required=True, help='')
    # p.add('--HEC_TLS', required=True, help='')
    # p.add('--HEC_TLS_VERIFY', required=True, help='')


    # #indexes', required=True, help='')
    # p.add('--indexes', required=True, help='')
    # #sourcetypes', required=True, help='')
    # p.add('--sourcetypes', required=True, help='')
    # p.add('--begin_date', required=True, help='')
    # p.add('--end_date', required=True, help='')
    # p.add('--extra', required=True, help='')

    # p.add('--log_level', required=True, help='')
    # p.add('--parition_units', required=True, help='')
    # p.add('--partition_interval', required=True, help='')
    # p.add('--directory', required=False, help='Directory to write data files to',default='../')
    # p.add('--parallel_processes', required=False, help='',default=1)
    # p.add('--job_location', required=False, help='Path to store the catalog for this job', default='../')
    # p.add('--job_name', required=True, help='Name for this job which will be a sub-directory of job_location')
    # p.add('--output_destination', required=False, default='file', help='file | hec | s3')
    # p.add('--gzip', required=True, help='')
    p.add('--output_format', required=False, help='json | raw | csv',default='json')
    p.add('--resume_mode', required=False, help='', default='false')
    p.add('--incremental_mode', required=False, help='', default='false')
    p.add('--incremental_time_source', required=False, help='file | search', default="file")
    p.add('--max_file_size_mb', default='0', help='')
    p.add('--sample_ratio', default='0', help='The integer value used to calculate the sample ratio. The formula is 1 / <integer>.')
    p.add('--keep_n_jobs', default=10, help='Number of previous partition files to keep')
    p.add('--s3_uri', default='', help='The full path of the bucket to write files to ie s3://export-test-tmuth/test1/test1.txt')
   
    # global options
    global options
    options = p.parse_args()
    # print(options)
    # print(p.format_help())
    print(p.format_values())
    # options_hash = checksum_var(p.format_values())
    # time.sleep(60)
    token_match=re.search("%.+%",options.s3_uri)
    if token_match:
        print(options.s3_uri)
        env_var=re.sub(r"%(.+)%","\\1",options.s3_uri)
        print(env_var)
        env_var_val=os.environ.get(env_var)
        print(env_var_val)
load_config()