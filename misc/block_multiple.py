import time
from tendo import singleton
print("Printed immediately.")
try:
   current_instance = singleton.SingleInstance()
   pass
except singleton.SingleInstanceException:
    raise SystemExit('Error: multiple instances of splunk-export with the same options cannot run simultaneously.')

time.sleep(30)