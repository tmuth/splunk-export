import logging,sys,os
from datetime import datetime
from time import sleep
import json

from multiprocessing import Process
# from pythonjsonlogger import jsonlogger


logger = logging.getLogger(__name__)  




logger_meta = logging.getLogger("meta")
logger_progress = logging.getLogger("progress") 
# logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)

# class CustomJsonFormatter(jsonlogger.JsonFormatter):
#     def add_fields(self, log_record,record, message_dict):
#         super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
#         if not log_record.get('timestamp'):
#             # this doesn't use record.created, so it is slightly off
#             now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
#             log_record['timestamp'] = now
#         if log_record.get('level'):
#             log_record['level'] = log_record['level'].upper()
#         else:
#             log_record['level'] = record.levelname

# logHandler = logging.StreamHandler()
# formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(module)s  %(name)s %(message)s')
# formatter = jsonlogger.JsonFormatter()
# logHandler.setFormatter(formatter)
# logger.addHandler(logHandler)

# logger_meta.addHandler(logHandler)

logging.basicConfig(level=logging.DEBUG,
                    format='{"timestamp": "%(asctime)s.%(msecs)03d", "name": "%(name)s", "module": "%(funcName)s", "level": "%(levelname)s", "message": "%(message)s"}',
                    datefmt='%Y-%m-%dT%H:%M:%S')

def hello():
 
    # print("hello")
    logger.info('So should this')
    sleep(1)
    logger_meta.info('So should this')

    for x in range(1, 10):
        logger_progress.info(x)
        # print(x)
        sleep(0.2)

def main():
    
    
    # logging.basicConfig(level=logging.DEBUG,
    #                 format='%(asctime)s %(name)-12s %(funcName)s %(levelname)-8s %(message)s',
    #                 datefmt='%m-%d %H:%M:%S')
    

    
    # logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    logger.debug('This message should go to the log file')
    logger.info('So should this')
    logger.warning('And this, too')
    hello()

def print_func(continent='Asia'):
    print('The name of continent is : ', continent)
    logger.info('Inside subprocess')
    logger_meta.info('Also in subprocess')

if __name__ == "__main__":
    main()
    names = ['America', 'Europe', 'Africa']
    procs = []
    proc = Process(target=print_func)  # instantiating without any argument
    procs.append(proc)
    proc.start()

    # instantiating process with arguments
    for name in names:
        # print(name)
        proc = Process(target=print_func, args=(name,))
        procs.append(proc)
        proc.start()

    # complete the processes
    for proc in procs:
        proc.join()