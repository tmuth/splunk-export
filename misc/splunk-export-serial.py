import time
from pprint import pprint
import json
import sys
import os
import logging
from splunk_http_event_collector import http_event_collector
import timeout_decorator
import configparser

if len(sys.argv) < 2:
    print "Pass the name of a config file as argument 1"
    exit(1)

if not os.path.exists(sys.argv[1]):
    print "Cannot find the configuration file: "+sys.argv[1]
    exit(1)

config = configparser.ConfigParser()
config.read(sys.argv[1])

